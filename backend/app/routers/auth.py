from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select, update

from ..audit import log_event
from ..config import get_settings
from ..deps import DB, CurrentUser
from ..errors import ApiError
from ..models import RefreshToken, User, utcnow
from ..ratelimit import limit
from ..schemas import LoginIn, LoginOut, PasswordChange, UserOut
from ..security import (create_access_token, hash_password, hash_token, new_refresh_token, password_problem,
                        verify_password)

router = APIRouter(prefix="/auth", tags=["auth"])
COOKIE = "gst_refresh"
MAX_FAILS, LOCK_MINUTES = 5, 15


def _set_cookie(resp: Response, raw: str) -> None:
    s = get_settings()
    resp.set_cookie(COOKIE, raw, max_age=s.refresh_token_days * 86400, httponly=True, secure=s.cookie_secure,
                    samesite=s.cookie_samesite, path="/api/v1/auth")


def _check_origin(request: Request) -> None:
    """Defence in depth against CSRF on cookie-authenticated endpoints (SameSite is the first layer)."""
    origin = request.headers.get("origin")
    if origin and origin not in get_settings().cors_origin_list and origin.split("://")[-1] != request.headers.get("host"):
        raise ApiError(403, "forbidden", "Origine non autorisée.")


def _issue(db, user: User, resp: Response) -> LoginOut:
    raw, digest = new_refresh_token()
    db.add(RefreshToken(user_id=user.id, token_hash=digest,
                        expires_at=utcnow() + timedelta(days=get_settings().refresh_token_days)))
    _set_cookie(resp, raw)
    token, ttl = create_access_token(user.id, user.role)
    return LoginOut(access_token=token, expires_in=ttl, user=UserOut.model_validate(user))


@router.post("/login", response_model=LoginOut, dependencies=[Depends(limit("login", "rate_limit_login"))])
def login(body: LoginIn, request: Request, response: Response, db: DB):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    now = utcnow()
    locked = bool(user and user.locked_until and user.locked_until > now)
    ok = verify_password(body.password, user.password_hash if user else None)
    if not user or locked or not ok or not user.active:
        if user and not locked and not ok:
            user.failed_logins += 1
            if user.failed_logins >= MAX_FAILS:
                user.locked_until, user.failed_logins = now + timedelta(minutes=LOCK_MINUTES), 0
            log_event(db, "user", user.id, "login_failed", None, {"email": user.email})
        db.commit()  # persist the counters even though we raise
        raise ApiError(401, "invalid_credentials", "Email ou mot de passe incorrect.")
    user.failed_logins, user.locked_until, user.last_login_at = 0, None, now
    log_event(db, "user", user.id, "login", user)
    return _issue(db, user, response)


@router.post("/refresh", response_model=LoginOut)
def refresh(request: Request, response: Response, db: DB):
    _check_origin(request)
    raw = request.cookies.get(COOKIE)
    if not raw:
        raise ApiError(401, "unauthorized", "Session absente.")
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)))
    now = utcnow()
    if not row:
        raise ApiError(401, "unauthorized", "Session invalide.")
    if row.revoked_at is not None:
        # Re-use of a rotated token => assume theft, revoke the whole family.
        db.execute(update(RefreshToken).where(RefreshToken.user_id == row.user_id, RefreshToken.revoked_at.is_(None))
                   .values(revoked_at=now))
        db.commit()
        raise ApiError(401, "unauthorized", "Session invalide.")
    exp = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=now.tzinfo)
    user = db.get(User, row.user_id)
    if exp < now or not user or not user.active:
        raise ApiError(401, "token_expired", "Session expirée.")
    row.revoked_at = now
    return _issue(db, user, response)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: DB):
    _check_origin(request)
    raw = request.cookies.get(COOKIE)
    if raw:
        row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)))
        if row and row.revoked_at is None:
            row.revoked_at = utcnow()
    response.delete_cookie(COOKIE, path="/api/v1/auth")


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return UserOut.model_validate(user)


@router.post("/change-password", status_code=204)
def change_password(body: PasswordChange, user: CurrentUser, db: DB):
    if not verify_password(body.current_password, user.password_hash):
        raise ApiError(400, "invalid_password", "Mot de passe actuel incorrect.")
    if problem := password_problem(body.new_password):
        raise ApiError(422, "weak_password", problem)
    user.password_hash, user.password_changed_at = hash_password(body.new_password), utcnow()
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
               .values(revoked_at=utcnow()))
    log_event(db, "user", user.id, "password_changed", user)

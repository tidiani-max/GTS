from fastapi import APIRouter
from sqlalchemy import func, select, update

from ..audit import log_event
from ..deps import DB, CurrentUser, Reader, SuperAdmin
from ..errors import ApiError
from ..models import DEFAULT_PREFS, ROLE_LEVEL, RefreshToken, User, utcnow
from ..schemas import ProfileUpdate, UserCreate, UserOut, UserUpdate
from ..security import hash_password, password_problem

router = APIRouter(tags=["users"])


def _active_super_admins(db) -> int:
    return db.scalar(select(func.count()).select_from(User).where(User.role == "super_admin", User.active.is_(True))) or 0


@router.get("/users", response_model=list[UserOut])
def list_users(db: DB, _: Reader):
    return [UserOut.model_validate(u) for u in db.scalars(select(User).order_by(User.id)).all()]


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, db: DB, actor: SuperAdmin):
    if problem := password_problem(body.password):
        raise ApiError(422, "weak_password", problem)
    if db.scalar(select(User.id).where(User.email == body.email.lower())):
        raise ApiError(409, "conflict", "Un utilisateur avec cet email existe déjà.")
    u = User(name=body.name, email=body.email.lower(), role=body.role, job_title=body.job_title,
             password_hash=hash_password(body.password), prefs=dict(DEFAULT_PREFS), password_changed_at=utcnow())
    db.add(u)
    db.flush()
    log_event(db, "user", u.id, "created", actor, {"email": u.email, "role": u.role})
    return UserOut.model_validate(u)


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate, db: DB, actor: SuperAdmin):
    u = db.get(User, user_id)
    if not u:
        raise ApiError(404, "not_found", "Utilisateur introuvable.")
    data = body.model_dump(exclude_unset=True)
    losing_super = u.role == "super_admin" and (data.get("role", u.role) != "super_admin" or data.get("active", u.active) is False)
    if losing_super and _active_super_admins(db) <= 1:
        raise ApiError(409, "last_super_admin", "Impossible : il doit rester au moins un super-administrateur actif.")
    changes = {}
    if pw := data.pop("password", None):
        if problem := password_problem(pw):
            raise ApiError(422, "weak_password", problem)
        u.password_hash, u.password_changed_at = hash_password(pw), utcnow()
        db.execute(update(RefreshToken).where(RefreshToken.user_id == u.id, RefreshToken.revoked_at.is_(None))
                   .values(revoked_at=utcnow()))
        changes["password"] = "reset"
    for k, v in data.items():
        if getattr(u, k) != v:
            changes[k] = [getattr(u, k), v]
            setattr(u, k, v)
    if data.get("active") is False:
        db.execute(update(RefreshToken).where(RefreshToken.user_id == u.id, RefreshToken.revoked_at.is_(None))
                   .values(revoked_at=utcnow()))
    if changes:
        log_event(db, "user", u.id, "updated", actor, changes)
    return UserOut.model_validate(u)


@router.patch("/me", response_model=UserOut)
def update_profile(body: ProfileUpdate, db: DB, user: CurrentUser):
    data = body.model_dump(exclude_unset=True)
    if "email" in data and data["email"].lower() != user.email:
        if db.scalar(select(User.id).where(User.email == data["email"].lower())):
            raise ApiError(409, "conflict", "Cet email est déjà utilisé.")
        user.email = data["email"].lower()
    if "prefs" in data:
        user.prefs = {**DEFAULT_PREFS, **{k: v for k, v in data["prefs"].items() if k in DEFAULT_PREFS}}
    for k in ("name", "job_title"):
        if k in data:
            setattr(user, k, data[k])
    log_event(db, "user", user.id, "profile_updated", user)
    return UserOut.model_validate(user)

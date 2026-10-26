from typing import Annotated

import jwt
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from .db import get_db
from .errors import ApiError
from .models import ROLE_LEVEL, User
from .security import decode_access_token

DB = Annotated[Session, Depends(get_db)]


def current_user(request: Request, db: DB) -> User:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise ApiError(401, "unauthorized", "Authentification requise.", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = decode_access_token(header[7:])
    except jwt.ExpiredSignatureError:
        raise ApiError(401, "token_expired", "Session expirée.", headers={"WWW-Authenticate": "Bearer"})
    except jwt.PyJWTError:
        raise ApiError(401, "unauthorized", "Jeton invalide.", headers={"WWW-Authenticate": "Bearer"})
    user = db.get(User, int(payload["sub"]))
    # Role and active flag always come from the database, never from the token.
    if not user or not user.active:
        raise ApiError(401, "unauthorized", "Compte inactif ou introuvable.")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require(min_role: str):
    """Server-side RBAC: readonly < staff < admin < super_admin."""
    def dep(user: CurrentUser) -> User:
        if ROLE_LEVEL[user.role] < ROLE_LEVEL[min_role]:
            raise ApiError(403, "forbidden", "Droits insuffisants pour cette action.")
        return user
    return dep


Reader = Annotated[User, Depends(require("readonly"))]
Staff = Annotated[User, Depends(require("staff"))]
Admin = Annotated[User, Depends(require("admin"))]
SuperAdmin = Annotated[User, Depends(require("super_admin"))]

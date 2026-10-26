import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud
from .. import models as m
from .. import schemas as s
from ..db import get_db
from ..deps import admin_user, staff_user

router = APIRouter(prefix="/settings", tags=["settings"])
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _all(db: Session) -> dict:
    return {k: crud.get_setting(db, k) for k in ("company", "notifications", "automation")}


def _validate(body: s.SettingsPayload) -> None:
    if body.company is not None:
        if set(body.company) - {"name", "publicEmail", "address"}:
            raise HTTPException(422, "Champs société inconnus.")
        if any(not isinstance(v, str) or len(v) > 300 for v in body.company.values()):
            raise HTTPException(422, "Valeur société invalide.")
    if body.notifications is not None:
        if set(body.notifications) - set(crud.DEFAULT_SETTINGS["notifications"]) or \
                any(not isinstance(v, bool) for v in body.notifications.values()):
            raise HTTPException(422, "Préférences de notification invalides.")
    if body.automation is not None:
        allowed = crud.DEFAULT_SETTINGS["automation"]
        for k, v in body.automation.items():
            if k not in allowed:
                raise HTTPException(422, f"Clé d'automatisation inconnue : {k}")
            if k == "recipients":
                if not isinstance(v, list) or len(v) > 20 or not all(isinstance(x, str) and EMAIL_RE.match(x) for x in v):
                    raise HTTPException(422, "Destinataires invalides (liste d'emails, 20 max).")
                continue
            if not isinstance(v, dict) or set(v) - set(allowed[k]):
                raise HTTPException(422, f"Configuration invalide pour {k}.")
            for kk, vv in v.items():
                if kk in ("enabled", "email"):
                    ok = isinstance(vv, bool)
                else:
                    lim = {"intervalMinutes": (1, 10080), "leadDays": (0, 30), "repeatDays": (1, 60), "weekday": (0, 6),
                           "hour": (0, 23), "maxAttempts": (1, 10), "retentionDays": (7, 3650)}[kk]
                    ok = isinstance(vv, int) and not isinstance(vv, bool) and lim[0] <= vv <= lim[1]
                if not ok:
                    raise HTTPException(422, f"Valeur invalide pour {k}.{kk}")


@router.get("")
def get_settings_(db: Session = Depends(get_db), _=Depends(staff_user)):
    return _all(db)


@router.put("")
def update_settings(body: s.SettingsPayload, db: Session = Depends(get_db), user: m.User = Depends(admin_user)):
    _validate(body)
    for key in ("company", "notifications", "automation"):
        val = getattr(body, key)
        if val is not None:
            crud.set_setting(db, key, val)
    crud.audit(db, "settings", "app", "updated", user, sections=[k for k in ("company", "notifications", "automation")
                                                                  if getattr(body, k) is not None])
    return _all(db)

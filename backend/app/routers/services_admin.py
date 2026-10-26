from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import crud
from .. import models as m
from .. import schemas as s
from ..db import get_db
from ..deps import admin_user, staff_user

router = APIRouter(prefix="/services", tags=["services"])


def _out(r: m.Service) -> s.ServiceOut:
    return s.ServiceOut(id=r.code, title=r.title, description=r.description, active=r.active)


def _get(db: Session, code: str) -> m.Service:
    r = db.scalar(select(m.Service).where(m.Service.code == code))
    if not r:
        raise HTTPException(404, "Service introuvable.")
    return r


@router.get("", response_model=list[s.ServiceOut])
def list_services(db: Session = Depends(get_db), _=Depends(staff_user)):
    return [_out(r) for r in db.scalars(select(m.Service).order_by(m.Service.code))]


@router.post("", response_model=s.ServiceOut, status_code=201)
def create_service(body: s.ServiceIn, db: Session = Depends(get_db), user: m.User = Depends(admin_user)):
    r = m.Service(code=crud.next_code(db, m.Service, "SER", 1, 2), title=" ".join(body.title.split()),
                  description=body.description, active=body.active)
    db.add(r)
    db.flush()
    crud.audit(db, "service", r.code, "created", user, title=r.title)
    return _out(r)


@router.patch("/{code}", response_model=s.ServiceOut)
def update_service(code: str, body: s.ServicePatch, db: Session = Depends(get_db), user: m.User = Depends(admin_user)):
    r = _get(db, code)
    d = body.model_dump(exclude_unset=True)
    for f, v in d.items():
        if v is not None:
            setattr(r, f, " ".join(v.split()) if f == "title" else v)
    crud.audit(db, "service", r.code, "updated", user, fields=sorted(d))
    db.flush()
    return _out(r)


@router.delete("/{code}", status_code=204)
def delete_service(code: str, db: Session = Depends(get_db), user: m.User = Depends(admin_user)):
    r = _get(db, code)
    crud.audit(db, "service", r.code, "deleted", user, title=r.title)
    db.delete(r)

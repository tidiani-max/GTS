from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import crud
from .. import models as m
from .. import schemas as s
from ..db import get_db
from ..deps import admin_user, staff_user

router = APIRouter(prefix="/clients", tags=["clients"])


def _out(db: Session, c: m.Client) -> s.ClientOut:
    n = db.scalar(select(func.count()).select_from(m.Project).where(m.Project.client_id == c.id)) or 0
    return s.ClientOut(id=c.code, name=c.name, contactName=c.contact_name, email=c.email, phone=c.phone, projects=n)


def _get(db: Session, code: str) -> m.Client:
    c = db.scalar(select(m.Client).where(m.Client.code == code))
    if not c:
        raise HTTPException(404, "Client introuvable.")
    return c


@router.get("", response_model=list[s.ClientOut])
def list_clients(db: Session = Depends(get_db), _=Depends(staff_user)):
    return [_out(db, c) for c in db.scalars(select(m.Client).order_by(m.Client.name))]


@router.post("", response_model=s.ClientOut, status_code=201)
def create_client(body: s.ClientIn, db: Session = Depends(get_db), user: m.User = Depends(admin_user)):
    if db.scalar(select(m.Client.id).where(func.lower(m.Client.name) == body.name.strip().lower())):
        raise HTTPException(409, "Un client portant ce nom existe déjà.")
    c = m.Client(code=crud.next_code(db, m.Client, "CLI", 1, 3), name=" ".join(body.name.split()),
                 contact_name=body.contactName, email=body.email, phone=body.phone)
    db.add(c)
    try:
        db.flush()
    except IntegrityError:
        raise HTTPException(409, "Un client portant ce nom existe déjà.")
    crud.audit(db, "client", c.code, "created", user, name=c.name)
    return _out(db, c)


@router.patch("/{code}", response_model=s.ClientOut)
def update_client(code: str, body: s.ClientPatch, db: Session = Depends(get_db), user: m.User = Depends(admin_user)):
    c = _get(db, code)
    d = body.model_dump(exclude_unset=True)
    mapping = {"name": "name", "contactName": "contact_name", "email": "email", "phone": "phone"}
    for f, v in d.items():
        if v is not None:
            setattr(c, mapping[f], " ".join(v.split()))
    crud.audit(db, "client", c.code, "updated", user, fields=sorted(d))
    try:
        db.flush()
    except IntegrityError:
        raise HTTPException(409, "Un client portant ce nom existe déjà.")
    return _out(db, c)


@router.delete("/{code}", status_code=204)
def delete_client(code: str, db: Session = Depends(get_db), user: m.User = Depends(admin_user)):
    c = _get(db, code)
    crud.audit(db, "client", c.code, "deleted", user, name=c.name)
    db.delete(c)  # projects keep existing (client_id -> NULL)

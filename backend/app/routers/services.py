from fastapi import APIRouter
from sqlalchemy import func, select

from ..audit import log_event
from ..deps import DB, Admin, Reader
from ..errors import ApiError
from ..models import Service
from ..schemas import ServiceIn, ServiceOut, ServicePatch
from ..serializers import service_out

router = APIRouter(prefix="/services", tags=["services"])


def _get(db, ref: str) -> Service:
    s = db.scalar(select(Service).where(Service.reference == ref))
    if not s:
        raise ApiError(404, "not_found", "Service introuvable.")
    return s


@router.get("", response_model=list[ServiceOut])
def list_services(db: DB, _: Reader):
    return [service_out(s) for s in db.scalars(select(Service).order_by(Service.sort_order, Service.id)).all()]


@router.post("", response_model=ServiceOut, status_code=201)
def create_service(body: ServiceIn, db: DB, user: Admin):
    top = db.scalar(select(func.max(Service.sort_order))) or 0
    s = Service(title=body.title, description=body.description, active=body.active, sort_order=top + 1)
    db.add(s)
    db.flush()
    s.reference = f"SER-{s.id:02d}"
    log_event(db, "service", s.reference, "created", user, {"title": s.title})
    return service_out(s)


@router.patch("/{ref}", response_model=ServiceOut)
def update_service(ref: str, body: ServicePatch, db: DB, user: Admin):
    s = _get(db, ref)
    changes = {}
    for k, v in body.model_dump(exclude_unset=True).items():
        if getattr(s, k) != v:
            changes[k] = [getattr(s, k), v]
            setattr(s, k, v)
    if changes:
        log_event(db, "service", s.reference, "updated", user, changes)
    return service_out(s)


@router.delete("/{ref}", status_code=204)
def delete_service(ref: str, db: DB, user: Admin):
    s = _get(db, ref)
    log_event(db, "service", s.reference, "deleted", user, {"title": s.title})
    db.delete(s)

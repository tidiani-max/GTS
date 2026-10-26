from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from ..audit import log_event
from ..csvutil import csv_response
from ..deps import DB, Admin, Reader, Staff
from ..errors import ApiError
from ..models import Client, Project, User
from ..pagination import PageParams, order_by_param, paginate
from ..schemas import ClientOut, Page, ProjectIn, ProjectOut, ProjectPatch
from ..serializers import project_out
from ..services.notifier import admins, notify

router = APIRouter(tags=["projects"])
SORTS = {"created_at": Project.created_at, "name": Project.name, "deadline": Project.deadline,
         "progress": Project.progress, "status": Project.status}


def _client(db, name: str) -> Client | None:
    name = name.strip()
    if not name:
        return None
    c = db.scalar(select(Client).where(func.lower(Client.name) == name.lower()))
    if not c:
        c = Client(name=name)
        db.add(c)
        db.flush()
    return c


def _lead(db, lead_id: int | None) -> User | None:
    if lead_id is None:
        return None
    u = db.get(User, lead_id)
    if not u or not u.active:
        raise ApiError(422, "validation_error", "Responsable introuvable ou inactif.")
    return u


def _get(db, ref: str) -> Project:
    p = db.scalar(select(Project).where(Project.reference == ref))
    if not p:
        raise ApiError(404, "not_found", "Projet introuvable.")
    return p


class PFilters:
    def __init__(self, q: str = "", status: str = "", sort: str = "-created_at"):
        self.q, self.status, self.sort = q, status, sort


def _query(f: PFilters):
    stmt = select(Project).join(Client, isouter=True)
    if f.q:
        like = f"%{f.q.strip().lower().replace('%', '').replace('_', '')}%"
        stmt = stmt.where(func.lower(Project.name).like(like) | func.lower(Client.name).like(like) |
                          func.lower(Project.service).like(like) | func.lower(Project.reference).like(like))
    if f.status:
        stmt = stmt.where(Project.status.in_(f.status.split(",")))
    return stmt.order_by(*order_by_param(Project, f.sort, SORTS, "created_at"))


@router.get("/projects", response_model=Page[ProjectOut])
def list_projects(db: DB, _: Reader, params: PageParams = Depends(), f: PFilters = Depends()):
    return paginate(db, _query(f), params, project_out, unique=True)


@router.get("/projects/export.csv")
def export_projects(db: DB, _: Reader, f: PFilters = Depends()):
    rows = [project_out(p) for p in db.scalars(_query(f)).unique().all()]
    return csv_response("projets-gst.csv", ["Référence", "Projet", "Client", "Service", "Statut", "Progression (%)",
                                            "Échéance", "Responsable"],
                        [[r.id, r.name, r.client, r.service, r.status, r.progress, r.deadline or "", r.lead] for r in rows])


@router.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectIn, db: DB, user: Admin):
    p = Project(name=body.name, service=body.service, status=body.status, progress=body.progress,
                deadline=body.deadline)
    p.client, p.lead = _client(db, body.client), _lead(db, body.lead_id)
    db.add(p)
    db.flush()
    p.reference = f"PRJ-{p.id:03d}"
    log_event(db, "project", p.reference, "created", user, {"name": p.name})
    return project_out(p)


@router.get("/projects/{ref}", response_model=ProjectOut)
def get_project(ref: str, db: DB, _: Reader):
    return project_out(_get(db, ref))


@router.patch("/projects/{ref}", response_model=ProjectOut)
def update_project(ref: str, body: ProjectPatch, db: DB, user: Staff):
    p = _get(db, ref)
    data = body.model_dump(exclude_unset=True)
    changes = {}
    old_status = p.status
    if "client" in data:
        new_client = _client(db, data.pop("client") or "")
        if (new_client.id if new_client else None) != p.client_id:
            changes["client"] = [p.client.name if p.client else None, new_client.name if new_client else None]
            p.client = new_client
    if "lead_id" in data:
        lead = _lead(db, data.pop("lead_id"))
        if (lead.id if lead else None) != p.lead_id:
            changes["lead"] = [p.lead.name if p.lead else None, lead.name if lead else None]
            p.lead, p.lead_id = lead, (lead.id if lead else None)
    for k, v in data.items():
        if getattr(p, k) != v:
            changes[k] = [str(getattr(p, k)), str(v)]
            setattr(p, k, v)
    if changes:
        log_event(db, "project", p.reference, "updated", user, changes)
    if p.status != old_status:
        notify(db, [u for u in admins(db) if u.id != user.id], "project_status",
               f"Projet {p.reference} : {old_status} → {p.status}", p.name, "/admin/projets",
               pref="project_status")
    return project_out(p)


@router.delete("/projects/{ref}", status_code=204)
def delete_project(ref: str, db: DB, user: Admin):
    p = _get(db, ref)
    log_event(db, "project", p.reference, "deleted", user, {"name": p.name})
    db.delete(p)


@router.get("/clients", response_model=list[ClientOut])
def list_clients(db: DB, _: Reader):
    return [ClientOut.model_validate(c) for c in db.scalars(select(Client).order_by(Client.name)).all()]

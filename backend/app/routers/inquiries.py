from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from ..audit import log_event
from ..csvutil import csv_response
from ..deps import DB, Admin, Reader, Staff
from ..errors import ApiError
from ..models import AuditEvent, Inquiry, InquiryNote, User, utcnow
from ..pagination import PageParams, order_by_param, paginate
from ..schemas import (
    HistoryOut,
    InquiryCreate,
    InquiryOut,
    InquiryUpdate,
    NoteIn,
    NoteOut,
    Page,
)
from ..serializers import inquiry_out, note_out
from ..services.notifier import notify

router = APIRouter(prefix="/inquiries", tags=["inquiries"])

# Allowed status transitions (workflow). Closed inquiries can only be re-opened.
TRANSITIONS = {
    "Nouveau": {"À étudier", "En cours", "Résolu", "Rejeté"},
    "À étudier": {"Nouveau", "En cours", "Résolu", "Rejeté"},
    "En cours": {"Nouveau", "À étudier", "Résolu", "Rejeté"},
    "Résolu": {"En cours", "À étudier"},
    "Rejeté": {"À étudier", "En cours"},
}
SORTS = {
    "created_at": Inquiry.created_at,
    "name": Inquiry.name,
    "status": Inquiry.status,
    "priority": Inquiry.priority,
    "follow_up": Inquiry.follow_up,
    "service": Inquiry.service,
}


class Filters:
    def __init__(
        self,
        q: str = "",
        status: str = "",
        priority: str = "",
        assignee_id: str = "",
        service: str = "",
        unread: bool | None = None,
        overdue: bool | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        sort: str = "-created_at",
    ):
        self.__dict__.update(locals())


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def build_query(f: Filters):
    stmt = select(Inquiry)
    if f.q:
        like = f"%{_escape(f.q.strip().lower())}%"
        from sqlalchemy import func

        stmt = stmt.where(
            or_(
                *(
                    func.lower(c).like(like, escape="\\")
                    for c in (
                        Inquiry.name,
                        Inquiry.company,
                        Inquiry.email,
                        Inquiry.reference,
                        Inquiry.service,
                        Inquiry.message,
                    )
                )
            )
        )
    if f.status:
        stmt = stmt.where(Inquiry.status.in_(f.status.split(",")))
    if f.priority:
        stmt = stmt.where(Inquiry.priority.in_(f.priority.split(",")))
    if f.assignee_id == "none":
        stmt = stmt.where(Inquiry.assignee_id.is_(None))
    elif f.assignee_id.isdigit():
        stmt = stmt.where(Inquiry.assignee_id == int(f.assignee_id))
    if f.service:
        stmt = stmt.where(Inquiry.service == f.service)
    if f.unread is not None:
        stmt = stmt.where(Inquiry.unread.is_(f.unread))
    if f.overdue:
        stmt = stmt.where(
            Inquiry.follow_up < date.today(),
            Inquiry.status.in_(("Nouveau", "À étudier", "En cours")),
        )
    if f.date_from:
        stmt = stmt.where(Inquiry.created_at >= f.date_from)
    if f.date_to:
        from datetime import timedelta

        stmt = stmt.where(Inquiry.created_at < f.date_to + timedelta(days=1))
    return stmt.order_by(*order_by_param(Inquiry, f.sort, SORTS, "created_at"))


def get_or_404(db, ref: str) -> Inquiry:
    inq = db.scalar(
        select(Inquiry)
        .where(Inquiry.reference == ref)
        .options(selectinload(Inquiry.notes))
    )
    if not inq:
        raise ApiError(404, "not_found", "Demande introuvable.")
    return inq


@router.get("", response_model=Page[InquiryOut])
def list_inquiries(
    db: DB, _: Reader, params: PageParams = Depends(), f: Filters = Depends()
):
    return paginate(db, build_query(f), params, inquiry_out, unique=True)


@router.get("/export.csv")
def export_csv(db: DB, _: Reader, f: Filters = Depends()):
    rows = [inquiry_out(i) for i in db.scalars(build_query(f)).unique().all()]
    return csv_response(
        "demandes-gst.csv",
        [
            "Référence",
            "Nom",
            "Société",
            "Email",
            "Téléphone",
            "Service",
            "Message",
            "Statut",
            "Priorité",
            "Assigné à",
            "Date de création",
            "Relance",
            "En retard",
        ],
        [
            [
                r.id,
                r.name,
                r.company,
                r.email,
                r.phone,
                r.service,
                r.message,
                r.status,
                r.priority,
                r.assignee,
                r.created_at.date().isoformat(),
                r.follow_up or "",
                "oui" if r.overdue else "non",
            ]
            for r in rows
        ],
    )


@router.post("", response_model=InquiryOut, status_code=201)
def create_inquiry(body: InquiryCreate, db: DB, user: Staff):
    if body.assignee_id and not db.get(User, body.assignee_id):
        raise ApiError(422, "validation_error", "Responsable introuvable.")
    inq = Inquiry(
        name=body.name,
        email=body.email.lower(),
        message=body.message,
        service=body.service,
        phone=body.phone,
        company=body.company,
        status=body.status,
        priority=body.priority,
        assignee_id=body.assignee_id,
        follow_up=body.follow_up,
        unread=False,
        source="manual",
    )
    db.add(inq)
    db.flush()
    inq.reference = f"GST-{1000 + inq.id}"
    log_event(db, "inquiry", inq.reference, "created", user, {"source": "manual"})
    db.refresh(inq)
    return inquiry_out(inq, True)


@router.get("/{ref}", response_model=InquiryOut)
def get_inquiry(ref: str, db: DB, _: Reader):
    return inquiry_out(get_or_404(db, ref), True)


@router.patch("/{ref}", response_model=InquiryOut)
def update_inquiry(ref: str, body: InquiryUpdate, db: DB, user: Staff):
    inq = get_or_404(db, ref)
    data = body.model_dump(exclude_unset=True)
    changes: dict = {}
    if "status" in data and data["status"] != inq.status:
        if data["status"] not in TRANSITIONS[inq.status]:
            raise ApiError(
                422,
                "invalid_transition",
                f"Transition interdite : « {inq.status} » → « {data['status']} ».",
                [{"allowed": sorted(TRANSITIONS[inq.status])}],
            )
        changes["status"] = [inq.status, data["status"]]
        inq.status = data["status"]
        inq.resolved_at = utcnow() if inq.status in ("Résolu", "Rejeté") else None
    if "assignee_id" in data and data["assignee_id"] != inq.assignee_id:
        new = db.get(User, data["assignee_id"]) if data["assignee_id"] else None
        if data["assignee_id"] and (not new or not new.active):
            raise ApiError(
                422, "validation_error", "Responsable introuvable ou inactif."
            )
        changes["assignee"] = [
            inq.assignee.name if inq.assignee else None,
            new.name if new else None,
        ]
        inq.assignee_id, inq.assignee = (new.id if new else None), new
        if new and new.id != user.id:
            notify(
                db,
                [new],
                "assignment",
                f"Demande assignée : {inq.reference}",
                f"{inq.name}  {inq.service}",
                f"/admin/demandes?ref={inq.reference}",
            )
    if "follow_up" in data and data["follow_up"] != inq.follow_up:
        changes["follow_up"] = [
            str(inq.follow_up) if inq.follow_up else None,
            str(data["follow_up"]) if data["follow_up"] else None,
        ]
        inq.follow_up, inq.reminder_count, inq.last_reminded_at = (
            data["follow_up"],
            0,
            None,
        )
    for field in ("priority", "name", "company", "phone", "service"):
        if field in data and data[field] != getattr(inq, field):
            changes[field] = [getattr(inq, field), data[field]]
            setattr(inq, field, data[field])
    if "unread" in data:
        inq.unread = data["unread"]  # reading/unreading is not audited (noise)
    if changes:
        log_event(
            db,
            "inquiry",
            inq.reference,
            "status_changed" if list(changes) == ["status"] else "updated",
            user,
            changes,
        )
    inq.updated_at = utcnow()
    return inquiry_out(inq, True)


@router.post("/{ref}/notes", response_model=NoteOut, status_code=201)
def add_note(ref: str, body: NoteIn, db: DB, user: Staff):
    inq = get_or_404(db, ref)
    note = InquiryNote(inquiry_id=inq.id, author_id=user.id, body=body.body)
    db.add(note)
    db.flush()
    db.refresh(note)
    log_event(
        db, "inquiry", inq.reference, "note_added", user, {"note": body.body[:120]}
    )
    return note_out(note)


@router.get("/{ref}/history", response_model=list[HistoryOut])
def history(ref: str, db: DB, _: Reader):
    get_or_404(db, ref)
    rows = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.entity_type == "inquiry", AuditEvent.entity_id == ref)
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .limit(100)
    ).all()
    return [
        HistoryOut(
            id=r.id,
            action=r.action,
            actor=r.actor_label,
            details=r.details,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.delete("/{ref}", status_code=204)
def delete_inquiry(ref: str, db: DB, user: Admin):
    inq = get_or_404(db, ref)
    log_event(
        db,
        "inquiry",
        inq.reference,
        "deleted",
        user,
        {"name": inq.name, "service": inq.service},
    )
    db.delete(inq)

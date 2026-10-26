from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, text

from ..audit import log_event
from ..db import SessionLocal
from ..deps import DB
from ..models import ROLE_LEVEL, Inquiry, Service, User, utcnow
from ..ratelimit import limit
from ..schemas import CompanySettings, ContactIn
from ..services.notifier import admins, extra_recipient_emails, notify
from ..services.settings_store import get_automation, get_company

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/services")
def public_services(db: DB):
    rows = db.scalars(
        select(Service)
        .where(Service.active.is_(True))
        .order_by(Service.sort_order, Service.id)
    ).all()
    return [
        {"id": s.reference, "title": s.title, "description": s.description}
        for s in rows
    ]


@router.get("/company", response_model=CompanySettings)
def public_company(db: DB):
    return get_company(db)


@router.post(
    "/contact",
    status_code=201,
    dependencies=[Depends(limit("contact", "rate_limit_contact"))],
)
def submit_contact(body: ContactIn, db: DB):
    # Honeypot: bots fill the hidden field. Pretend success, store nothing.
    if body.website:
        return {
            "reference": "GST-0000",
            "message": "Merci, votre demande a bien été enregistrée.",
        }
    # Idempotency: the same person re-sending the same message within 10 minutes is not duplicated.
    dup = db.scalar(
        select(Inquiry).where(
            Inquiry.email == body.email.lower(),
            Inquiry.message == body.message,
            Inquiry.created_at >= utcnow() - timedelta(minutes=10),
        )
    )
    if dup:
        return {
            "reference": dup.reference,
            "message": "Merci, votre demande a bien été enregistrée.",
        }
    inq = Inquiry(
        name=body.name,
        email=body.email.lower(),
        message=body.message,
        service=body.service or "Demande générale",
        phone=body.phone,
        company=body.company,
        status="Nouveau",
        priority="Normale",
        unread=True,
        source="website",
    )
    db.add(inq)
    db.flush()
    inq.reference = f"GST-{1000 + inq.id}"
    log_event(db, "inquiry", inq.reference, "created", None, {"source": "website"})
    if get_automation(db).new_inquiry_enabled:
        title = f"Nouvelle demande {inq.reference}"
        text_body = f"{inq.name} ({inq.email})  {inq.service}\n\n{inq.message[:300]}"
        key = f"new:{inq.reference}"
        notify(
            db,
            admins(db),
            "new_inquiry",
            title,
            text_body,
            f"/admin/demandes?ref={inq.reference}",
            key,
            pref="new_inquiry",
        )
        extra_recipient_emails(db, title, text_body, key)
    return {
        "reference": inq.reference,
        "message": "Merci, votre demande a bien été enregistrée.",
    }

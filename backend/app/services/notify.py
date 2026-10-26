"""Create in-app notifications + queue e-mail (outbox). Idempotent through Notification.dedupe_key."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import crud
from .. import models as m
from ..config import get_settings


def admins(db: Session) -> list[m.User]:
    return list(
        db.scalars(
            select(m.User).where(
                m.User.active.is_(True), m.User.role.in_(("admin", "super_admin"))
            )
        )
    )


def notify(
    db: Session,
    *,
    user: m.User | None,
    email_to: str | None,
    kind: str,
    title: str,
    body: str,
    link: str,
    dedupe_key: str,
    email: bool = True,
) -> m.Notification | None:
    """Insert unless dedupe_key already exists. Returns the new row or None if duplicate."""
    if db.scalar(
        select(m.Notification.id).where(m.Notification.dedupe_key == dedupe_key)
    ):
        return None
    queue_mail = bool(email and email_to and get_settings().email_mode != "disabled")
    n = m.Notification(
        user_id=user.id if user else None,
        kind=kind,
        title=title,
        body=body,
        link=link,
        dedupe_key=dedupe_key,
        email_to=email_to if queue_mail else None,
        email_status="pending" if queue_mail else "none",
    )
    if user is None and not queue_mail:
        return None  # broadcast rows only exist to carry an e-mail
    db.add(n)
    db.flush()
    return n


def notify_new_inquiry(db: Session, inq: m.Inquiry) -> int:
    prefs = crud.get_setting(db, "notifications")
    if not prefs.get("newInquiry", True):
        return 0
    auto = crud.get_setting(db, "automation")
    count = 0
    title = f"Nouvelle demande {inq.code}"
    body = f"{inq.name} ({inq.email})  {inq.service}\n\n{inq.message[:500]}"
    for u in admins(db):
        if notify(
            db,
            user=u,
            email_to=u.email,
            kind="new_inquiry",
            title=title,
            body=body,
            link=f"/admin/demandes?open={inq.code}",
            dedupe_key=f"new:{inq.code}:u{u.id}",
        ):
            count += 1
    for addr in auto.get("recipients", []):
        if notify(
            db,
            user=None,
            email_to=addr,
            kind="new_inquiry",
            title=title,
            body=body,
            link="",
            dedupe_key=f"new:{inq.code}:{addr}",
        ):
            count += 1
    return count

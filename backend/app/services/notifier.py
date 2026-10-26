"""In-app notifications + queued email, honouring per-user preferences and de-duplication keys."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import DEFAULT_PREFS, ROLE_LEVEL, Notification, User
from .emailer import enqueue_email
from .settings_store import get_automation


def admins(db: Session) -> list[User]:
    return [u for u in db.scalars(select(User).where(User.active.is_(True))).all()
            if ROLE_LEVEL[u.role] >= ROLE_LEVEL["admin"]]


def notify(db: Session, users: list[User], kind: str, title: str, body: str, link: str = "",
           dedupe_key: str | None = None, pref: str | None = None, email: bool = True) -> int:
    """Returns the number of users actually notified (0 when de-duplicated / opted out)."""
    count, seen = 0, set()
    for u in users:
        if u.id in seen or not u.active:
            continue
        seen.add(u.id)
        if pref and not {**DEFAULT_PREFS, **(u.prefs or {})}.get(pref, True):
            continue
        key = f"{dedupe_key}" if dedupe_key else None
        if key and db.scalar(select(Notification.id).where(Notification.user_id == u.id, Notification.dedupe_key == key)):
            continue
        db.add(Notification(user_id=u.id, kind=kind, title=title, body=body, link=link, dedupe_key=key))
        if email:
            enqueue_email(db, u.email, title, f"{body}\n\n{link}".strip(), f"{key}:{u.id}" if key else None)
        count += 1
    return count


def extra_recipient_emails(db: Session, title: str, body: str, dedupe_key: str | None) -> None:
    for addr in get_automation(db).extra_recipients:
        enqueue_email(db, str(addr), title, body, f"{dedupe_key}:x:{addr}" if dedupe_key else None)

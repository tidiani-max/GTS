"""Shared helpers: code generation, audit trail, serialisers, settings access."""
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models as m
from . import schemas as s

DEFAULT_SETTINGS = {
    "company": {
        "name": "Global Services Technologie",
        "publicEmail": "dcheick93@hotmail.com",
        "address": "Hamdallaye ACI-2000 · Rue 420 Porte 437 · BP 2485 Bamako, Mali",
    },
    "notifications": {
        "newInquiry": True,
        "projectStatus": True,
        "followUpDue": True,
        "monthlyReport": True,
    },
    "automation": {
        "recipients": [],  # extra e-mail recipients for summaries / new inquiries
        "followup_reminders": {"enabled": True, "intervalMinutes": 60, "leadDays": 0, "email": True},
        "overdue_alerts": {"enabled": True, "intervalMinutes": 360, "repeatDays": 3, "email": True},
        "weekly_summary": {"enabled": True, "weekday": 0, "hour": 7, "email": True},
        "deliver_emails": {"enabled": True, "intervalMinutes": 5, "maxAttempts": 5},
        "cleanup": {"enabled": True, "intervalMinutes": 1440, "retentionDays": 90},
    },
}


def get_setting(db: Session, key: str) -> dict:
    row = db.get(m.AppSetting, key)
    base = DEFAULT_SETTINGS[key]
    if not row:
        return _copy(base)
    merged = _copy(base)
    _deep_update(merged, row.value or {})
    return merged


def set_setting(db: Session, key: str, value: dict) -> dict:
    merged = get_setting(db, key)
    _deep_update(merged, value)
    row = db.get(m.AppSetting, key)
    if row:
        row.value = merged
    else:
        db.add(m.AppSetting(key=key, value=merged))
    db.flush()
    return merged


def _copy(d):
    import copy
    return copy.deepcopy(d)


def _deep_update(base: dict, new: dict) -> None:
    for k, v in new.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_update(base[k], v)
        else:
            base[k] = v


def next_code(db: Session, model, prefix: str, start: int, width: int = 0) -> str:
    """Next human-readable code (GST-1049, PRJ-022...). Retried by callers on unique collisions."""
    codes = db.scalars(select(model.code).where(model.code.like(f"{prefix}-%"))).all()
    nums = [int(c.split("-")[1]) for c in codes if c.split("-")[1].isdigit()]
    n = max(nums, default=start - 1) + 1
    return f"{prefix}-{n:0{width}d}" if width else f"{prefix}-{n}"


def audit(db: Session, entity_type: str, entity_id: str, action: str, actor: m.User | None, **details) -> None:
    db.add(m.AuditEvent(entity_type=entity_type, entity_id=entity_id, action=action,
                        actor_id=actor.id if actor else None, actor_name=actor.name if actor else "Système",
                        details=details))


def iso(d: date | datetime | None) -> str:
    return d.isoformat()[:10] if d else ""


def user_out(u: m.User) -> s.UserOut:
    return s.UserOut(id=u.code, name=u.name, email=u.email, role=u.role, jobTitle=u.job_title, active=u.active)


def inquiry_out(i: m.Inquiry, with_notes: bool = True) -> s.InquiryOut:
    return s.InquiryOut(
        id=i.code, name=i.name, company=i.company, email=i.email, phone=i.phone, service=i.service,
        message=i.message, status=i.status, priority=i.priority,
        assignee=i.assignee.name if i.assignee else "Non assigné",
        assigneeId=i.assignee.code if i.assignee else None,
        createdAt=iso(i.created_at), followUp=iso(i.follow_up) or "À planifier", unread=i.unread,
        notes=[n.body for n in i.notes] if with_notes else [],
        noteItems=[s.NoteOut(id=n.id, body=n.body, author=n.author_name, createdAt=n.created_at) for n in i.notes]
        if with_notes else [])


def project_out(p: m.Project) -> s.ProjectOut:
    return s.ProjectOut(id=p.code, name=p.name, client=p.client.name if p.client else "", service=p.service,
                        status=p.status, progress=p.progress, deadline=iso(p.deadline),
                        lead=p.lead.name if p.lead else "Non assigné", leadId=p.lead.code if p.lead else None)


def get_or_create_client(db: Session, name: str) -> m.Client | None:
    name = name.strip()
    if not name:
        return None
    c = db.scalar(select(m.Client).where(func.lower(m.Client.name) == name.lower()))
    if not c:
        c = m.Client(code=next_code(db, m.Client, "CLI", 1, 3), name=name)
        db.add(c)
        db.flush()
    return c

from sqlalchemy.orm import Session

from .models import AuditEvent, User


def log_event(db: Session, entity_type: str, entity_id: str | int, action: str, actor: User | None = None,
              details: dict | None = None) -> AuditEvent:
    ev = AuditEvent(entity_type=entity_type, entity_id=str(entity_id), action=action,
                    actor_id=actor.id if actor else None, actor_label=actor.name if actor else "Système",
                    details=details or {})
    db.add(ev)
    return ev

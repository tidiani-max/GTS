from fastapi import APIRouter, Depends
from sqlalchemy import select

from ..deps import DB, Admin
from ..models import AuditEvent
from ..pagination import PageParams, paginate
from ..schemas import HistoryOut, Page

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=Page[HistoryOut])
def list_audit(db: DB, _: Admin, params: PageParams = Depends(), entity_type: str = "", action: str = ""):
    stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
    if entity_type:
        stmt = stmt.where(AuditEvent.entity_type == entity_type)
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    return paginate(db, stmt, params, lambda r: HistoryOut(
        id=r.id, action=f"{r.entity_type}.{r.entity_id}: {r.action}", actor=r.actor_label, details=r.details,
        created_at=r.created_at))

from fastapi import APIRouter, Query
from sqlalchemy import func, select, update

from ..deps import DB, CurrentUser
from ..errors import ApiError
from ..models import Notification, utcnow
from ..schemas import NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _out(n: Notification) -> NotificationOut:
    return NotificationOut(id=n.id, kind=n.kind, title=n.title, body=n.body, link=n.link, read=n.read_at is not None,
                           created_at=n.created_at)


@router.get("")
def list_notifications(db: DB, user: CurrentUser, unread_only: bool = False, limit: int = Query(30, ge=1, le=100)):
    stmt = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    items = db.scalars(stmt.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit)).all()
    unread = db.scalar(select(func.count()).select_from(Notification).where(
        Notification.user_id == user.id, Notification.read_at.is_(None))) or 0
    return {"items": [_out(n) for n in items], "unreadCount": unread}


@router.post("/{nid}/read", status_code=204)
def mark_read(nid: int, db: DB, user: CurrentUser):
    n = db.get(Notification, nid)
    if not n or n.user_id != user.id:
        raise ApiError(404, "not_found", "Notification introuvable.")
    n.read_at = n.read_at or utcnow()


@router.post("/read-all", status_code=204)
def mark_all_read(db: DB, user: CurrentUser):
    db.execute(update(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None))
               .values(read_at=utcnow()))

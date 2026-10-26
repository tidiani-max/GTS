"""Dashboard + reports: every number is computed from the database (no hard-coded totals)."""
from collections import Counter
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .. import crud
from .. import models as m
from ..db import get_db
from ..deps import staff_user

router = APIRouter(prefix="/stats", tags=["stats"])
MONTHS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]


def _aware(dt: datetime | None) -> datetime | None:
    return dt.replace(tzinfo=timezone.utc) if dt and dt.tzinfo is None else dt


def _buckets(today: date, days: int):
    """30 days -> weekly buckets; otherwise monthly buckets covering the range."""
    if days <= 31:
        start = today - timedelta(days=days - 1)
        out = []
        for i in range(0, days, 7):
            a = start + timedelta(days=i)
            b = min(a + timedelta(days=6), today)
            out.append((f"{a.day:02d}/{a.month:02d}", a, b))
        return out
    n = max(1, round(days / 30))
    y, mo = today.year, today.month
    months = []
    for _ in range(n):
        months.append((y, mo))
        mo -= 1
        if mo == 0:
            y, mo = y - 1, 12
    out = []
    for y, mo in reversed(months):
        a = date(y, mo, 1)
        b = (date(y + (mo == 12), mo % 12 + 1, 1)) - timedelta(days=1)
        out.append((MONTHS[mo - 1], a, b))
    return out


@router.get("/overview")
def overview(days: int = Query(180, ge=7, le=730), db: Session = Depends(get_db), _=Depends(staff_user)):
    today = date.today()
    inquiries = db.scalars(select(m.Inquiry).options(selectinload(m.Inquiry.assignee))
                           .order_by(m.Inquiry.created_at.desc())).all()
    projects = db.scalars(select(m.Project).options(selectinload(m.Project.client), selectinload(m.Project.lead))
                          .order_by(m.Project.deadline.asc())).all()
    since = datetime.combine(today - timedelta(days=days), datetime.min.time(), tzinfo=timezone.utc)
    in_range = [i for i in inquiries if _aware(i.created_at) >= since]

    trend = []
    for label, a, b in _buckets(today, days):
        demandes = sum(1 for i in inquiries if a <= _aware(i.created_at).date() <= b)
        resolues = sum(1 for i in inquiries if i.resolved_at and a <= _aware(i.resolved_at).date() <= b)
        trend.append({"month": label, "demandes": demandes, "resolues": resolues})

    this_m = sum(1 for i in inquiries if _aware(i.created_at).date() >= today.replace(day=1))
    prev_end = today.replace(day=1) - timedelta(days=1)
    prev_m = sum(1 for i in inquiries if prev_end.replace(day=1) <= _aware(i.created_at).date() <= prev_end)
    change = round((this_m - prev_m) / prev_m * 100) if prev_m else None

    resolved = [i for i in in_range if i.status == "Résolu"]
    durations = [(_aware(i.resolved_at) - _aware(i.created_at)).total_seconds() / 86400 for i in resolved if i.resolved_at]
    by_service = Counter(i.service for i in in_range)
    status_counts = [{"name": s, "value": sum(1 for i in in_range if i.status == s)} for s in m.INQUIRY_STATUSES]
    return {
        "rangeDays": days,
        "kpis": {
            "total": len(in_range),
            "toProcess": sum(1 for i in inquiries if i.status in ("Nouveau", "À étudier")),
            "unread": sum(1 for i in inquiries if i.unread),
            "overdue": sum(1 for i in inquiries if i.status in m.OPEN_STATUSES and i.follow_up and i.follow_up < today),
            "activeProjects": sum(1 for p in projects if p.status == "En cours"),
            "monthChangePct": change,
            "receivedThisMonth": this_m,
        },
        "trend": trend,
        "statusCounts": status_counts,
        "byService": [{"name": k, "value": v} for k, v in by_service.most_common()],
        "resolutionRate": round(len(resolved) / len(in_range) * 100) if in_range else 0,
        "avgResolutionDays": round(sum(durations) / len(durations), 1) if durations else None,
        "projectsDone": sum(1 for p in projects if p.status == "Terminé"),
        "projectsTotal": len(projects),
        "recentInquiries": [crud.inquiry_out(i, with_notes=False).model_dump() for i in inquiries[:4]],
        "ongoingProjects": [crud.project_out(p).model_dump() for p in projects if p.status == "En cours"][:3],
    }


@router.get("/summary-preview")
def summary_preview(db: Session = Depends(get_db), _=Depends(staff_user)):
    from ..services.automation import build_summary
    return build_summary(db, date.today())

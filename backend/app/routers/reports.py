from collections import Counter
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from ..csvutil import csv_response
from ..deps import DB, Reader
from ..models import INQUIRY_STATUSES, OPEN_STATUSES, PRIORITIES, Inquiry, Project

router = APIRouter(prefix="/reports", tags=["reports"])
MONTHS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]
RANGES = {"30d": 1, "3m": 3, "6m": 6, "12m": 12}


def _aware(d: datetime | None) -> datetime | None:
    return d.replace(tzinfo=timezone.utc) if d and d.tzinfo is None else d


def _month_starts(n: int, today: date) -> list[date]:
    y, m = today.year, today.month
    out = []
    for _ in range(max(n, 1)):
        out.append(date(y, m, 1))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return out[::-1]


def compute(db, range_: str) -> dict:
    today = date.today()
    months = _month_starts(RANGES.get(range_, 6) if range_ != "30d" else 1, today)
    start = datetime.combine(today - timedelta(days=30) if range_ == "30d" else months[0], datetime.min.time(), tzinfo=timezone.utc)
    inquiries = db.scalars(select(Inquiry)).unique().all()
    projects = db.scalars(select(Project)).unique().all()
    in_range = [i for i in inquiries if _aware(i.created_at) >= start]
    resolved_in_range = [i for i in inquiries if i.resolved_at and i.status == "Résolu" and _aware(i.resolved_at) >= start]

    trend = []
    for ms in months:
        nxt = date(ms.year + (ms.month == 12), ms.month % 12 + 1, 1)
        trend.append({"month": MONTHS[ms.month - 1],
                      "demandes": sum(1 for i in inquiries if ms <= _aware(i.created_at).date() < nxt),
                      "resolues": sum(1 for i in inquiries if i.resolved_at and i.status == "Résolu" and ms <= _aware(i.resolved_at).date() < nxt)})
    delays = [(_aware(i.resolved_at) - _aware(i.created_at)).total_seconds() / 86400 for i in resolved_in_range]
    last30 = sum(1 for i in inquiries if _aware(i.created_at) >= datetime.now(timezone.utc) - timedelta(days=30))
    prev30 = sum(1 for i in inquiries if datetime.now(timezone.utc) - timedelta(days=60) <= _aware(i.created_at)
                 < datetime.now(timezone.utc) - timedelta(days=30))
    status_counts, service_counts = Counter(i.status for i in in_range), Counter(i.service for i in in_range)
    total_all = len(inquiries)
    resolved_all = sum(1 for i in inquiries if i.status == "Résolu")
    return {
        "range": range_,
        "kpis": {
            "totalInquiries": total_all, "inquiriesInRange": len(in_range),
            "toTreat": sum(1 for i in inquiries if i.status in ("Nouveau", "À étudier")),
            "unread": sum(1 for i in inquiries if i.unread),
            "overdue": sum(1 for i in inquiries if i.follow_up and i.follow_up < today and i.status in OPEN_STATUSES),
            "activeProjects": sum(1 for p in projects if p.status == "En cours"),
            "completedProjects": sum(1 for p in projects if p.status == "Terminé"), "totalProjects": len(projects),
            "resolutionRate": round(resolved_all / total_all * 100) if total_all else 0,
            "avgResolutionDays": round(sum(delays) / len(delays), 1) if delays else None,
            "last30Days": last30, "previous30Days": prev30,
            "trendPct": round((last30 - prev30) / prev30 * 100) if prev30 else None,
        },
        "trend": trend,
        "byStatus": [{"name": s, "value": status_counts.get(s, 0)} for s in INQUIRY_STATUSES],
        "byPriority": [{"name": p, "value": sum(1 for i in in_range if i.priority == p)} for p in PRIORITIES],
        "byService": [{"name": k, "value": v} for k, v in service_counts.most_common()],
        "projectsByStatus": [{"name": s, "value": sum(1 for p in projects if p.status == s)}
                             for s in ("Planifié", "En cours", "Suspendu", "Terminé")],
    }


@router.get("/overview")
def overview(db: DB, _: Reader, range: str = Query("6m", pattern="^(30d|3m|6m|12m)$")):
    return compute(db, range)


@router.get("/overview.csv")
def overview_csv(db: DB, _: Reader, range: str = Query("6m", pattern="^(30d|3m|6m|12m)$")):
    r = compute(db, range)
    rows = [["Indicateur", k, v] for k, v in r["kpis"].items()]
    rows += [["Mois", t["month"], f"{t['demandes']} demandes / {t['resolues']} résolues"] for t in r["trend"]]
    rows += [["Statut", x["name"], x["value"]] for x in r["byStatus"]]
    rows += [["Service", x["name"], x["value"]] for x in r["byService"]]
    return csv_response(f"rapport-gst-{range}.csv", ["Catégorie", "Clé", "Valeur"], rows)

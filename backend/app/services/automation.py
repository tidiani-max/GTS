"""Automation jobs. Every job: records a JobRun, supports dry-run, is idempotent (dedupe keys),
and never performs risky actions (it only creates notifications/emails and deletes expired technical data)."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..models import (
    OPEN_STATUSES,
    AuditEvent,
    EmailOutbox,
    Inquiry,
    JobRun,
    Notification,
    Project,
    RefreshToken,
    User,
    utcnow,
)
from .emailer import deliver_pending
from .notifier import admins, extra_recipient_emails, notify
from .settings_store import get_automation

log = logging.getLogger("gst.automation")

JOBS = {
    "follow_up_reminders": "Rappels de relance (demandes ouvertes avec échéance)",
    "overdue_alerts": "Alerte quotidienne des demandes en retard",
    "send_emails": "Envoi des emails en attente (retry/backoff)",
    "weekly_summary": "Résumé hebdomadaire d'activité",
    "cleanup": "Nettoyage des jetons/données techniques expirés",
}
INTERVAL_KEY = {
    "follow_up_reminders": "reminders_every_minutes",
    "overdue_alerts": "overdue_every_minutes",
}


def _recipients(db: Session, inq: Inquiry, notify_assignee: bool) -> list[User]:
    if notify_assignee and inq.assignee and inq.assignee.active:
        return [inq.assignee]
    return admins(db)


def follow_up_reminders(db: Session, dry_run: bool) -> dict:
    cfg, today = get_automation(db), date.today()
    if not cfg.reminders_enabled:
        return {"skipped": "disabled"}
    horizon = today + timedelta(days=cfg.reminder_lead_days)
    gap_limit = utcnow() - timedelta(hours=cfg.reminder_min_gap_hours)
    rows = (
        db.scalars(
            select(Inquiry).where(
                Inquiry.status.in_(OPEN_STATUSES),
                Inquiry.follow_up.is_not(None),
                Inquiry.follow_up >= today,
                Inquiry.follow_up <= horizon,
                Inquiry.reminder_count < cfg.max_reminders,
                (Inquiry.last_reminded_at.is_(None))
                | (Inquiry.last_reminded_at <= gap_limit),
            )
        )
        .unique()
        .all()
    )
    out = {"eligible": len(rows), "notified": 0, "items": []}
    for inq in rows:
        out["items"].append(inq.reference)
        if dry_run:
            continue
        n = inq.reminder_count + 1
        title = f"Relance à effectuer : {inq.reference}"
        body = (
            f"{inq.name} ({inq.service})  relance prévue le {inq.follow_up:%d/%m/%Y}."
        )
        key = f"reminder:{inq.reference}:{inq.follow_up.isoformat()}:{n}"
        out["notified"] += notify(
            db,
            _recipients(db, inq, cfg.notify_assignee),
            "reminder",
            title,
            body,
            f"/admin/demandes?ref={inq.reference}",
            key,
            pref="follow_up_due",
        )
        inq.reminder_count, inq.last_reminded_at = n, utcnow()
    return out


def overdue_alerts(db: Session, dry_run: bool) -> dict:
    cfg, today = get_automation(db), date.today()
    if not cfg.overdue_enabled:
        return {"skipped": "disabled"}
    rows = (
        db.scalars(
            select(Inquiry)
            .where(
                Inquiry.status.in_(OPEN_STATUSES),
                Inquiry.follow_up.is_not(None),
                Inquiry.follow_up < today,
            )
            .order_by(Inquiry.follow_up)
        )
        .unique()
        .all()
    )
    out = {
        "overdue": len(rows),
        "notified": 0,
        "items": [r.reference for r in rows][:50],
    }
    if not rows or dry_run:
        return out
    # One digest per day (not one message per inquiry) -> no spam.
    lines = "\n".join(
        f"- {r.reference} · {r.name} · échéance {r.follow_up:%d/%m/%Y}"
        for r in rows[:15]
    )
    title = f"{len(rows)} demande(s) en retard de suivi"
    key = f"overdue-digest:{today.isoformat()}"
    out["notified"] = notify(
        db,
        admins(db),
        "overdue",
        title,
        lines,
        "/admin/demandes?overdue=1",
        key,
        pref="follow_up_due",
    )
    extra_recipient_emails(db, title, lines, key)
    return out


def send_emails(db: Session, dry_run: bool) -> dict:
    return deliver_pending(db, dry_run=dry_run)


def weekly_summary(db: Session, dry_run: bool) -> dict:
    cfg, now = get_automation(db), utcnow()
    if not cfg.summary_enabled:
        return {"skipped": "disabled"}
    since = now - timedelta(days=7)
    received = (
        db.scalar(
            select(func.count()).select_from(Inquiry).where(Inquiry.created_at >= since)
        )
        or 0
    )
    resolved = (
        db.scalar(
            select(func.count())
            .select_from(Inquiry)
            .where(Inquiry.resolved_at >= since)
        )
        or 0
    )
    open_n = (
        db.scalar(
            select(func.count())
            .select_from(Inquiry)
            .where(Inquiry.status.in_(OPEN_STATUSES))
        )
        or 0
    )
    overdue = (
        db.scalar(
            select(func.count())
            .select_from(Inquiry)
            .where(Inquiry.status.in_(OPEN_STATUSES), Inquiry.follow_up < date.today())
        )
        or 0
    )
    active_p = (
        db.scalar(
            select(func.count())
            .select_from(Project)
            .where(Project.status == "En cours")
        )
        or 0
    )
    iso = now.isocalendar()
    out = {
        "week": f"{iso.year}-W{iso.week:02d}",
        "received": received,
        "resolved": resolved,
        "open": open_n,
        "overdue": overdue,
        "active_projects": active_p,
    }
    if dry_run:
        return out
    body = (
        f"Résumé de la semaine {out['week']}\n- Demandes reçues : {received}\n- Demandes résolues : {resolved}\n"
        f"- Demandes ouvertes : {open_n} (dont {overdue} en retard)\n- Projets en cours : {active_p}"
    )
    key = f"summary:{out['week']}"
    out["notified"] = notify(
        db,
        admins(db),
        "summary",
        "Résumé hebdomadaire GST",
        body,
        "/admin/rapports",
        key,
        pref="monthly_report",
    )
    extra_recipient_emails(db, "Résumé hebdomadaire GST", body, key)
    return out


def cleanup(db: Session, dry_run: bool) -> dict:
    cfg, now = get_automation(db), utcnow()
    if not cfg.cleanup_enabled:
        return {"skipped": "disabled"}
    cutoff = now - timedelta(days=cfg.retention_days)
    queries = {
        "refresh_tokens": (
            RefreshToken,
            (RefreshToken.expires_at < now) | (RefreshToken.revoked_at < cutoff),
        ),
        "read_notifications": (
            Notification,
            Notification.read_at.is_not(None) & (Notification.created_at < cutoff),
        ),
        "sent_emails": (
            EmailOutbox,
            EmailOutbox.status.in_(("sent", "skipped"))
            & (EmailOutbox.created_at < cutoff),
        ),
        "job_runs": (JobRun, JobRun.started_at < cutoff),
    }
    out = {}
    for name, (model, cond) in queries.items():
        if dry_run:
            out[name] = (
                db.scalar(select(func.count()).select_from(model).where(cond)) or 0
            )
        else:
            out[name] = db.execute(delete(model).where(cond)).rowcount or 0
    return out  # Audit events are intentionally never auto-deleted.


RUNNERS = {
    "follow_up_reminders": follow_up_reminders,
    "overdue_alerts": overdue_alerts,
    "send_emails": send_emails,
    "weekly_summary": weekly_summary,
    "cleanup": cleanup,
}


def run_job(
    db: Session, name: str, dry_run: bool = False, trigger: str = "schedule"
) -> JobRun:
    """Run one job inside its own transaction; failures are recorded (visible in the admin UI), never raised."""
    if name not in RUNNERS:
        raise KeyError(name)
    run = JobRun(job=name, trigger=trigger, dry_run=dry_run, status="running")
    db.add(run)
    db.commit()
    try:
        summary = RUNNERS[name](db, dry_run)
        run.status, run.summary = "success", summary
        log.info(
            "job %s ok (dry_run=%s): %s",
            name,
            dry_run,
            {k: v for k, v in summary.items() if k != "items"},
        )
    except Exception as exc:
        db.rollback()
        run = db.get(JobRun, run.id)
        run.status, run.error = "failed", f"{type(exc).__name__}: {exc}"[:1000]
        log.exception("job %s failed", name)
    run.finished_at = utcnow()
    db.commit()
    return run


def is_due(db: Session, name: str, now: datetime | None = None) -> bool:
    cfg, now = get_automation(db), now or datetime.now(timezone.utc)
    last = db.scalar(
        select(func.max(JobRun.started_at)).where(
            JobRun.job == name, JobRun.trigger == "schedule", JobRun.dry_run.is_(False)
        )
    )
    if last and last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    if name == "weekly_summary":
        if (
            not cfg.summary_enabled
            or now.weekday() != cfg.summary_weekday
            or now.hour < cfg.summary_hour
        ):
            return False
        return not last or last.isocalendar()[:2] != now.isocalendar()[:2]
    if name == "send_emails":
        return not last or now - last >= timedelta(minutes=1)
    if name == "cleanup":
        return not last or now - last >= timedelta(hours=24)
    minutes = getattr(cfg, INTERVAL_KEY[name])
    return not last or now - last >= timedelta(minutes=minutes)


def next_due(db: Session, name: str) -> datetime | None:
    cfg = get_automation(db)
    last = db.scalar(
        select(func.max(JobRun.started_at)).where(
            JobRun.job == name, JobRun.trigger == "schedule", JobRun.dry_run.is_(False)
        )
    )
    if last and last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    if name == "weekly_summary":
        if not cfg.summary_enabled:
            return None
        now = datetime.now(timezone.utc)
        d = now + timedelta(days=(cfg.summary_weekday - now.weekday()) % 7)
        t = d.replace(hour=cfg.summary_hour, minute=0, second=0, microsecond=0)
        return t if t > now else t + timedelta(days=7)
    gap = {"send_emails": timedelta(minutes=1), "cleanup": timedelta(hours=24)}.get(
        name
    ) or timedelta(
        minutes=getattr(cfg, INTERVAL_KEY.get(name, "reminders_every_minutes"))
    )
    return (last + gap) if last else datetime.now(timezone.utc)

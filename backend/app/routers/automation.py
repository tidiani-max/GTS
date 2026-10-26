from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from ..audit import log_event
from ..config import get_settings
from ..deps import DB, Admin
from ..errors import ApiError
from ..models import EmailOutbox, JobRun
from ..pagination import PageParams, paginate
from ..schemas import AutomationConfig, EmailOut, JobRunOut, Page
from ..services.automation import JOBS, next_due, run_job
from ..services.settings_store import get_automation, set_automation

router = APIRouter(prefix="/automation", tags=["automation"])


@router.get("/status")
def status(db: DB, _: Admin):
    jobs = []
    for name, label in JOBS.items():
        last = db.scalar(select(JobRun).where(JobRun.job == name, JobRun.dry_run.is_(False)).order_by(JobRun.id.desc()).limit(1))
        failed = db.scalar(select(func.count()).select_from(JobRun).where(JobRun.job == name, JobRun.status == "failed")) or 0
        jobs.append({"name": name, "label": label, "nextDue": next_due(db, name),
                     "lastRun": JobRunOut.model_validate(last) if last else None, "failedRuns": failed})
    outbox = dict(db.execute(select(EmailOutbox.status, func.count()).group_by(EmailOutbox.status)).all())
    return {"config": get_automation(db), "jobs": jobs, "emailMode": get_settings().email_mode, "outbox": outbox}


@router.put("/config", response_model=AutomationConfig)
def update_config(body: AutomationConfig, db: DB, user: Admin):
    log_event(db, "settings", "automation", "updated", user, body.model_dump(mode="json"))
    return set_automation(db, body)


@router.post("/jobs/{name}/run", response_model=JobRunOut)
def run_now(name: str, db: DB, user: Admin, dry_run: bool = True):
    """Manual run. Defaults to dry-run=true: you must explicitly pass dry_run=false to act."""
    if name not in JOBS:
        raise ApiError(404, "not_found", "Tâche inconnue.")
    run = run_job(db, name, dry_run=dry_run, trigger="manual")
    log_event(db, "automation", name, "manual_run", user, {"dry_run": dry_run, "status": run.status})
    return JobRunOut.model_validate(run)


@router.get("/runs", response_model=Page[JobRunOut])
def runs(db: DB, _: Admin, params: PageParams = Depends(), job: str = "", status: str = ""):
    stmt = select(JobRun).order_by(JobRun.id.desc())
    if job:
        stmt = stmt.where(JobRun.job == job)
    if status:
        stmt = stmt.where(JobRun.status == status)
    return paginate(db, stmt, params, JobRunOut.model_validate)


@router.get("/emails", response_model=Page[EmailOut])
def emails(db: DB, _: Admin, params: PageParams = Depends(), status: str = ""):
    stmt = select(EmailOutbox).order_by(EmailOutbox.id.desc())
    if status:
        stmt = stmt.where(EmailOutbox.status == status)
    return paginate(db, stmt, params, EmailOut.model_validate)

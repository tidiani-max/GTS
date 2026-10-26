from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import crud
from .. import models as m
from .. import schemas as s
from ..config import get_settings
from ..db import get_db
from ..deps import admin_user
from ..services import automation

router = APIRouter(prefix="/jobs", tags=["automation"])


@router.get("")
def list_jobs(db: Session = Depends(get_db), _=Depends(admin_user)):
    auto = crud.get_setting(db, "automation")
    jobs = []
    for name, (label, desc) in automation.JOB_LABELS.items():
        last = db.scalar(select(m.JobRun).where(m.JobRun.job == name, m.JobRun.dry_run.is_(False))
                         .order_by(m.JobRun.id.desc()).limit(1))
        jobs.append({"name": name, "label": label, "description": desc, "config": auto[name],
                     "lastRun": s.JobRunOut(id=last.id, job=last.job, trigger=last.trigger, dryRun=last.dry_run,
                                            status=last.status, startedAt=last.started_at, finishedAt=last.finished_at,
                                            result=last.result or {}, error=last.error).model_dump() if last else None})
    outbox = dict(db.execute(select(m.Notification.email_status, func.count()).group_by(m.Notification.email_status)).all())
    return {"jobs": jobs, "recipients": auto.get("recipients", []), "emailMode": get_settings().email_mode,
            "outbox": {k: outbox.get(k, 0) for k in ("pending", "sent", "failed", "skipped")}}


@router.get("/runs", response_model=list[s.JobRunOut])
def runs(job: str | None = None, limit: int = 30, db: Session = Depends(get_db), _=Depends(admin_user)):
    stmt = select(m.JobRun).order_by(m.JobRun.id.desc()).limit(min(limit, 100))
    if job:
        stmt = stmt.where(m.JobRun.job == job)
    return [s.JobRunOut(id=r.id, job=r.job, trigger=r.trigger, dryRun=r.dry_run, status=r.status, startedAt=r.started_at,
                        finishedAt=r.finished_at, result=r.result or {}, error=r.error) for r in db.scalars(stmt)]


@router.post("/{name}/run")
def run(name: str, dry_run: bool = True, user: m.User = Depends(admin_user), db: Session = Depends(get_db)):
    """Manual run. Defaults to dry-run=true so nothing happens unless explicitly requested."""
    if name not in automation.JOBS:
        raise HTTPException(404, "Tâche inconnue.")
    crud.audit(db, "job", name, "manual_run", user, dry_run=dry_run)
    db.commit()
    return automation.run_job(name, trigger="manual", dry_run=dry_run)


@router.get("/outbox", response_model=list[s.NotificationOut])
def outbox(status: str | None = None, db: Session = Depends(get_db), _=Depends(admin_user)):
    stmt = select(m.Notification).where(m.Notification.email_status != "none").order_by(m.Notification.id.desc()).limit(50)
    if status:
        stmt = stmt.where(m.Notification.email_status == status)
    return [s.NotificationOut(id=n.id, kind=n.kind, title=f"{n.title} → {n.email_to}", body=n.body, link=n.link,
                              read=n.read_at is not None, emailStatus=n.email_status, emailAttempts=n.email_attempts,
                              emailError=n.email_error, createdAt=n.created_at) for n in db.scalars(stmt)]

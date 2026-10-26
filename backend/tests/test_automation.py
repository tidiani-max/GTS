from datetime import timedelta

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import EmailOutbox, Inquiry, JobRun, Notification, utcnow
from app.services import automation as A
from app.services.emailer import deliver_pending, enqueue_email
from app.services.settings_store import get_automation, set_automation


def count(model, *where):
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(model).where(*where))


def run(name, dry=False):
    with SessionLocal() as db:
        return A.run_job(db, name, dry_run=dry, trigger="manual")


def test_reminder_due_today_is_idempotent_and_not_spammy(make_inquiry, today):
    make_inquiry(follow_up=today, status="En cours")
    make_inquiry(follow_up=today + timedelta(days=5), status="En cours")  # not due yet
    make_inquiry(follow_up=today, status="Résolu")  # closed -> never reminded
    r1 = run("follow_up_reminders")
    assert r1.status == "success" and r1.summary["eligible"] == 1 and r1.summary["notified"] == 2  # unassigned -> both admins
    n = count(Notification, Notification.kind == "reminder")
    assert n == 2
    r2 = run("follow_up_reminders")  # second run within the min-gap: nothing new
    assert r2.summary["eligible"] == 0 and count(Notification, Notification.kind == "reminder") == n


def test_reminder_cap_and_reset_on_followup_change(make_inquiry, today):
    ref = make_inquiry(follow_up=today, status="En cours")
    with SessionLocal() as db:
        cfg = get_automation(db)
        cfg.reminder_min_gap_hours = 1
        cfg.max_reminders = 1
        set_automation(db, cfg)
        db.commit()
    run("follow_up_reminders")
    with SessionLocal() as db:  # simulate time passing
        i = db.scalar(select(Inquiry).where(Inquiry.reference == ref))
        i.last_reminded_at = utcnow() - timedelta(hours=5)
        db.commit()
    assert run("follow_up_reminders").summary["eligible"] == 0  # cap of 1 reached


def test_dry_run_changes_nothing(make_inquiry, today):
    make_inquiry(follow_up=today, status="Nouveau")
    r = run("follow_up_reminders", dry=True)
    assert r.dry_run and r.summary["eligible"] == 1 and r.summary["notified"] == 0
    assert count(Notification) == 0 and count(EmailOutbox) == 0


def test_overdue_digest_once_per_day(make_inquiry, today):
    make_inquiry(follow_up=today - timedelta(days=3), status="En cours")
    make_inquiry(follow_up=today - timedelta(days=9), status="À étudier")
    a = run("overdue_alerts")
    assert a.summary["overdue"] == 2 and a.summary["notified"] >= 1
    total = count(Notification, Notification.kind == "overdue")
    run("overdue_alerts")
    assert count(Notification, Notification.kind == "overdue") == total  # same-day digest is de-duplicated


def test_disabled_job_does_nothing(make_inquiry, today):
    make_inquiry(follow_up=today, status="Nouveau")
    with SessionLocal() as db:
        cfg = get_automation(db)
        cfg.reminders_enabled = False
        set_automation(db, cfg)
        db.commit()
    assert run("follow_up_reminders").summary == {"skipped": "disabled"}


def test_weekly_summary_once_per_week():
    assert run("weekly_summary").summary["week"]
    n = count(Notification, Notification.kind == "summary")
    run("weekly_summary")
    assert count(Notification, Notification.kind == "summary") == n


def test_job_failure_is_recorded_not_raised(monkeypatch):
    monkeypatch.setitem(A.RUNNERS, "cleanup", lambda db, dry: 1 / 0)
    r = run("cleanup")
    assert r.status == "failed" and "ZeroDivisionError" in r.error


def test_email_outbox_modes_retry_and_idempotency(monkeypatch):
    with SessionLocal() as db:
        assert enqueue_email(db, "a@b.c", "S", "B", "k1") is not None
        db.flush()
        assert enqueue_email(db, "a@b.c", "S", "B", "k1") is None  # idempotent
        db.commit()
    with SessionLocal() as db:
        res = deliver_pending(db)  # EMAIL_MODE=disabled in tests -> skipped, never sent
        db.commit()
    assert res["skipped"] == 1 and count(EmailOutbox, EmailOutbox.status == "skipped") == 1

    # retry/backoff path using the smtp branch with a failing transport
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "email_mode", "smtp")
    monkeypatch.setattr("app.services.emailer._smtp_send", lambda row: (_ for _ in ()).throw(OSError("down")))
    with SessionLocal() as db:
        enqueue_email(db, "x@y.z", "S2", "B2", "k2")
        db.commit()
        res = deliver_pending(db)
        db.commit()
    assert res["retry"] == 1
    with SessionLocal() as db:
        row = db.scalar(select(EmailOutbox).where(EmailOutbox.dedupe_key == "k2"))
        assert row.status == "pending" and row.attempts == 1 and "down" in row.last_error and row.next_attempt_at > utcnow()


def test_scheduler_due_logic():
    with SessionLocal() as db:
        assert A.is_due(db, "follow_up_reminders")  # never ran
    run("follow_up_reminders")
    with SessionLocal() as db:  # manual runs do not count as scheduled runs
        assert A.is_due(db, "follow_up_reminders")


def test_automation_api(client, auth):
    h = auth("admin")
    s = client.get("/api/v1/automation/status", headers=h).json()
    assert {j["name"] for j in s["jobs"]} == set(A.JOBS) and s["emailMode"] == "disabled"
    r = client.post("/api/v1/automation/jobs/follow_up_reminders/run", headers=h).json()
    assert r["dryRun"] is True and r["status"] == "success"  # manual runs are dry by default
    assert client.post("/api/v1/automation/jobs/nope/run", headers=h).status_code == 404
    cfg = {**s["config"], "remindersEveryMinutes": 30, "extraRecipients": ["boss@example.com"]}
    assert client.put("/api/v1/automation/config", json=cfg, headers=h).json()["remindersEveryMinutes"] == 30
    assert client.put("/api/v1/automation/config", json={**cfg, "remindersEveryMinutes": 1}, headers=h).status_code == 422
    assert client.get("/api/v1/automation/runs", headers=h).json()["total"] >= 1

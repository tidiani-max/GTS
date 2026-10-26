"""Email outbox with retry/backoff. Modes (EMAIL_MODE): console (log only, default) | smtp | disabled."""
import logging
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import EmailOutbox, utcnow

log = logging.getLogger("gst.email")
MAX_ATTEMPTS = 5


def enqueue_email(db: Session, to: str, subject: str, body: str, dedupe_key: str | None = None) -> EmailOutbox | None:
    """Queue an email in the caller's transaction. Idempotent when dedupe_key is given."""
    if dedupe_key and db.scalar(select(EmailOutbox.id).where(EmailOutbox.dedupe_key == dedupe_key)):
        return None
    row = EmailOutbox(to_email=to, subject=subject[:300], body=body, dedupe_key=dedupe_key)
    db.add(row)
    return row


def _smtp_send(row: EmailOutbox) -> None:
    s = get_settings()
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = s.email_from, row.to_email, row.subject
    msg.set_content(row.body)
    with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as smtp:
        if s.smtp_starttls:
            smtp.starttls()
        if s.smtp_user:
            smtp.login(s.smtp_user, s.smtp_password)
        smtp.send_message(msg)


def deliver_pending(db: Session, limit: int = 50, dry_run: bool = False) -> dict:
    mode = get_settings().email_mode
    now = utcnow()
    rows = db.scalars(select(EmailOutbox).where(EmailOutbox.status == "pending", EmailOutbox.next_attempt_at <= now)
                      .order_by(EmailOutbox.id).limit(limit)).all()
    result = {"mode": mode, "due": len(rows), "sent": 0, "failed": 0, "retry": 0, "skipped": 0}
    if dry_run:
        result["would_send"] = [{"to": r.to_email, "subject": r.subject} for r in rows]
        return result
    for row in rows:
        if mode == "disabled":
            row.status, result["skipped"] = "skipped", result["skipped"] + 1
            continue
        row.attempts += 1
        try:
            if mode == "smtp":
                _smtp_send(row)
            else:
                log.info("[EMAIL console] to=%s subject=%s\n%s", row.to_email, row.subject, row.body)
            row.status, row.sent_at, row.last_error = "sent", utcnow(), ""
            result["sent"] += 1
        except Exception as exc:  # network/SMTP errors are expected: retry with exponential backoff
            row.last_error = f"{type(exc).__name__}: {exc}"[:500]
            if row.attempts >= MAX_ATTEMPTS:
                row.status, result["failed"] = "failed", result["failed"] + 1
            else:
                row.next_attempt_at = datetime.now(timezone.utc) + timedelta(minutes=2 ** row.attempts)
                result["retry"] += 1
            log.warning("email %s attempt %s failed: %s", row.id, row.attempts, row.last_error)
    return result

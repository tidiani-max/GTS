"""E-mail transport. console = log only (default for dev/tests), smtp = real delivery, disabled = skip."""
import logging
import smtplib
import ssl
from email.message import EmailMessage

from ..config import get_settings

log = logging.getLogger("gst.mail")


class MailSkipped(Exception):
    pass


def send_email(to: str, subject: str, body: str) -> str:
    """Returns delivery mode used ('console' or 'smtp'). Raises on failure (caller handles retry)."""
    s = get_settings()
    if s.email_mode == "disabled":
        raise MailSkipped("EMAIL_MODE=disabled")
    if s.email_mode == "console" or s.environment == "test":
        log.info("[EMAIL console mode] to=%s subject=%s\n%s", to, subject, body)
        return "console"
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = s.email_from, to, subject
    msg.set_content(body)
    with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as smtp:
        if s.smtp_starttls:
            smtp.starttls(context=ssl.create_default_context())
        if s.smtp_user:
            smtp.login(s.smtp_user, s.smtp_password)
        smtp.send_message(msg)
    return "smtp"

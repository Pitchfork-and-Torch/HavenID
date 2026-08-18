from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.config import Settings


def send_mail(settings: Settings, to_addr: str, subject: str, body: str) -> bool:
    if not settings.smtp_host or not to_addr:
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or settings.smtp_user or "havenid@localhost"
    msg["To"] = to_addr
    msg.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        return True
    except Exception:
        return False

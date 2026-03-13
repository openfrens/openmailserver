from __future__ import annotations

import smtplib
from datetime import UTC, datetime
from email.message import EmailMessage
from email.utils import make_msgid
from smtplib import SMTPException

from sqlalchemy.orm import Session

from openmailserver.config import get_settings
from openmailserver.models import DeliveryEvent, Mailbox, OutboundMessage
from openmailserver.services.logging_service import write_system_log
from openmailserver.services.maildir_service import deliver_local_copy


def build_message(
    sender: str,
    recipients: list[str],
    subject: str,
    text_body: str | None,
    html_body: str | None,
    cc: list[str],
    bcc: list[str],
) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    if cc:
        message["Cc"] = ", ".join(cc)
    message["Subject"] = subject
    message["Message-Id"] = make_msgid(domain=sender.split("@", 1)[1])
    if text_body and html_body:
        message.set_content(text_body)
        message.add_alternative(html_body, subtype="html")
    elif html_body:
        message.add_alternative(html_body, subtype="html")
    else:
        message.set_content(text_body or "")
    return message


def send_outbound_message(
    db: Session,
    sender: str,
    recipients: list[str],
    subject: str,
    text_body: str | None = None,
    html_body: str | None = None,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
) -> OutboundMessage:
    settings = get_settings()
    cc = cc or []
    bcc = bcc or []
    message = build_message(sender, recipients, subject, text_body, html_body, cc, bcc)
    raw_mime = message.as_string()

    record = OutboundMessage(
        sender=sender,
        recipients=recipients,
        cc=cc,
        bcc=bcc,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        raw_mime=raw_mime,
        message_id=message["Message-Id"],
        state="queued",
    )
    db.add(record)
    db.flush()

    try:
        if settings.transport_mode == "maildir":
            for recipient in recipients:
                deliver_local_copy(recipient, message.as_bytes())
            record.state = "sent"
            record.sent_at = datetime.now(UTC)
        else:
            with smtplib.SMTP(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout_seconds,
            ) as smtp:
                smtp.send_message(message, from_addr=sender, to_addrs=recipients + cc + bcc)
            record.state = "sent"
            record.sent_at = datetime.now(UTC)
    except (OSError, SMTPException) as exc:
        record.state = "failed"
        record.error = str(exc)
        write_system_log(db, "error", "outbound_send_failed", str(exc), {"message_id": record.id})
    finally:
        event = DeliveryEvent(
            outbound_message_id=record.id,
            event_type=record.state,
            details={"queue_id": record.queue_id, "error": record.error},
        )
        db.add(event)
        write_system_log(
            db,
            "info",
            "outbound_send",
            f"Processed outbound message {record.id}",
            {"state": record.state},
        )

    local_mailbox = db.query(Mailbox).filter(Mailbox.email == sender).first()
    if local_mailbox:
        deliver_local_copy(sender, message.as_bytes())
    return record

from __future__ import annotations

import mailbox
from email import policy
from email.parser import BytesParser
from pathlib import Path

from openmailserver.config import get_settings
from openmailserver.schemas import MailboxMessageRead, MailboxMessageSummary


def mailbox_path(email_address: str) -> Path:
    settings = get_settings()
    local_part, domain = email_address.split("@", 1)
    return settings.maildir_root / domain / local_part


def ensure_maildir(email_address: str) -> Path:
    path = mailbox_path(email_address)
    path.parent.mkdir(parents=True, exist_ok=True)
    mailbox.Maildir(path, create=True)
    return path


def list_messages(email_address: str) -> list[MailboxMessageSummary]:
    path = ensure_maildir(email_address)
    maildir = mailbox.Maildir(path, factory=None, create=True)
    messages: list[MailboxMessageSummary] = []
    for key, raw in maildir.iteritems():
        parsed = BytesParser(policy=policy.default).parsebytes(raw.as_bytes())
        messages.append(
            MailboxMessageSummary(
                id=str(key),
                subject=parsed.get("Subject"),
                from_address=parsed.get("From"),
                to=parsed.get("To"),
                date=parsed.get("Date"),
            )
        )
    return sorted(messages, key=lambda item: item.date or "", reverse=True)


def get_message(email_address: str, message_id: str) -> MailboxMessageRead | None:
    path = ensure_maildir(email_address)
    maildir = mailbox.Maildir(path, factory=None, create=True)
    if message_id not in maildir:
        return None
    raw = maildir[message_id]
    parsed = BytesParser(policy=policy.default).parsebytes(raw.as_bytes())
    body = ""
    if parsed.is_multipart():
        for part in parsed.walk():
            if part.get_content_type().startswith("text/") and not part.get_filename():
                body += part.get_content()
    else:
        body = parsed.get_content()
    return MailboxMessageRead(
        id=message_id,
        subject=parsed.get("Subject"),
        from_address=parsed.get("From"),
        to=parsed.get("To"),
        date=parsed.get("Date"),
        body=body,
    )


def deliver_local_copy(email_address: str, raw_message: bytes) -> str:
    path = ensure_maildir(email_address)
    maildir = mailbox.Maildir(path, factory=None, create=True)
    return str(maildir.add(raw_message))

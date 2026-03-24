from __future__ import annotations

import imaplib
import ssl
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime

from openmailserver.config import Settings, get_settings
from openmailserver.schemas import MailboxMessageRead, MailboxMessageSummary
from openmailserver.services.maildir_service import (
    get_message as get_maildir_message,
)
from openmailserver.services.maildir_service import (
    list_messages as list_maildir_messages,
)
from openmailserver.services.runtime_secret_service import mailbox_password_for


class MailboxReadError(RuntimeError):
    pass


def _message_summary(message_id: str, raw_message: bytes) -> MailboxMessageSummary:
    parsed = BytesParser(policy=policy.default).parsebytes(raw_message)
    return MailboxMessageSummary(
        id=message_id,
        subject=parsed.get("Subject"),
        from_address=parsed.get("From"),
        to=parsed.get("To"),
        date=parsed.get("Date"),
    )


def _message_body(raw_message: bytes) -> MailboxMessageRead:
    parsed = BytesParser(policy=policy.default).parsebytes(raw_message)
    body = ""
    if parsed.is_multipart():
        for part in parsed.walk():
            if part.get_content_type().startswith("text/") and not part.get_filename():
                body += part.get_content()
    else:
        body = parsed.get_content()
    return MailboxMessageRead(
        id="",
        subject=parsed.get("Subject"),
        from_address=parsed.get("From"),
        to=parsed.get("To"),
        date=parsed.get("Date"),
        body=body,
    )


def _mailbox_password(address: str, settings: Settings) -> str | None:
    if settings.transport_mode == "maildir":
        return None
    return mailbox_password_for(address, settings)


def _ssl_context(verify_tls: bool) -> ssl.SSLContext:
    context = ssl.create_default_context()
    if not verify_tls:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context


@contextmanager
def _imap_client(
    address: str, password: str, settings: Settings
) -> Iterator[imaplib.IMAP4]:
    security = settings.imap_security.lower()
    host = settings.effective_imap_host
    timeout = settings.imap_timeout_seconds
    context = _ssl_context(settings.imap_verify_tls)
    try:
        if security == "ssl":
            client = imaplib.IMAP4_SSL(
                host=host,
                port=settings.imap_port,
                ssl_context=context,
                timeout=timeout,
            )
        else:
            client = imaplib.IMAP4(host=host, port=settings.imap_port, timeout=timeout)
            if security == "starttls":
                client.starttls(ssl_context=context)
        client.login(address, password)
        status, _ = client.select("INBOX", readonly=True)
        if status != "OK":
            raise MailboxReadError(f"Unable to open INBOX for {address}")
        yield client
    except (OSError, ssl.SSLError, imaplib.IMAP4.error) as exc:
        raise MailboxReadError(f"Unable to read mailbox {address}: {exc}") from exc
    finally:
        with suppress(Exception):
            client.logout()


def _imap_message_uids(client: imaplib.IMAP4) -> list[str]:
    status, data = client.uid("search", None, "ALL")
    if status != "OK":
        raise MailboxReadError("Unable to list mailbox messages")
    return [uid.decode("utf-8") for uid in data[0].split()]


def _imap_fetch_message(client: imaplib.IMAP4, message_id: str) -> bytes | None:
    status, data = client.uid("fetch", message_id, "(RFC822)")
    if status != "OK":
        raise MailboxReadError(f"Unable to fetch message {message_id}")
    for part in data:
        if isinstance(part, tuple):
            return part[1]
    return None


def list_messages(email_address: str) -> list[MailboxMessageSummary]:
    settings = get_settings()
    password = _mailbox_password(email_address, settings)
    if not password:
        return list_maildir_messages(email_address)
    with _imap_client(email_address, password, settings) as client:
        messages: list[tuple[float, MailboxMessageSummary]] = []
        for message_id in reversed(_imap_message_uids(client)):
            raw_message = _imap_fetch_message(client, message_id)
            if raw_message is None:
                continue
            summary = _message_summary(message_id, raw_message)
            try:
                sort_key = parsedate_to_datetime(summary.date).timestamp() if summary.date else 0.0
            except (TypeError, ValueError):
                sort_key = 0.0
            messages.append((sort_key, summary))
        return [message for _, message in sorted(messages, key=lambda item: item[0], reverse=True)]


def get_message(email_address: str, message_id: str) -> MailboxMessageRead | None:
    settings = get_settings()
    password = _mailbox_password(email_address, settings)
    if not password:
        return get_maildir_message(email_address, message_id)
    with _imap_client(email_address, password, settings) as client:
        raw_message = _imap_fetch_message(client, message_id)
        if raw_message is None:
            return None
        message = _message_body(raw_message)
        return MailboxMessageRead(
            id=message_id,
            subject=message.subject,
            from_address=message.from_address,
            to=message.to,
            date=message.date,
            body=message.body,
        )

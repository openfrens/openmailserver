from __future__ import annotations

import pytest

from openmailserver.api import mailboxes
from openmailserver.schemas import (
    AliasCreate,
    AliasRead,
    ApiKeyResponse,
    MailboxCreate,
    MailboxMessageRead,
    MailboxMessageSummary,
    MailboxProvisionResponse,
    MailboxRead,
)
from openmailserver.services.mailbox_service import MailboxExistsError


def test_create_mailbox_delegates_to_service(db_session, monkeypatch):
    response = MailboxProvisionResponse(
        mailbox=MailboxRead(id=1, email="agent@example.test", quota=256, active=True),
        password="secret-pass",
        api_key=ApiKeyResponse(key="mailbox_raw", scopes=["mail:read", "mail:send"]),
    )

    monkeypatch.setattr(
        mailboxes,
        "provision_mailbox",
        lambda db, payload: response,
    )

    result = mailboxes.create_mailbox(
        MailboxCreate(local_part="agent", domain="example.test", password="secret-pass", quota=256),
        db=db_session,
        _=object(),
    )

    assert result.mailbox.email == "agent@example.test"
    assert result.api_key.key == "mailbox_raw"


def test_create_mailbox_rejects_duplicate_address(db_session, monkeypatch):
    def raise_duplicate(db, payload):
        raise MailboxExistsError("Mailbox already exists")

    monkeypatch.setattr(mailboxes, "provision_mailbox", raise_duplicate)

    with pytest.raises(mailboxes.HTTPException, match="Mailbox already exists"):
        mailboxes.create_mailbox(
            MailboxCreate(local_part="agent", domain="example.test", password="secret-pass"),
            db=db_session,
            _=object(),
        )


def test_create_alias_and_message_helpers(db_session, monkeypatch):
    monkeypatch.setattr(
        mailboxes,
        "create_alias_record",
        lambda db, payload: AliasRead(
            id=1,
            source=str(payload.source),
            destination=str(payload.destination),
        ),
    )
    monkeypatch.setattr(
        mailboxes,
        "list_messages",
        lambda address: [
            MailboxMessageSummary(id="1", subject="Hello", from_address="sender@example.test", to=address)
        ],
    )
    monkeypatch.setattr(
        mailboxes,
        "get_message",
        lambda address, message_id: MailboxMessageRead(
            id=message_id,
            subject="Hello",
            from_address="sender@example.test",
            to=address,
            body="Body",
        ),
    )

    alias_response = mailboxes.create_alias(
        AliasCreate(source="alias@example.test", destination="agent@example.test"),
        db=db_session,
        _=object(),
    )
    messages = mailboxes.get_mailbox_messages("agent@example.test", _=object())
    message = mailboxes.get_mailbox_message("1", "agent@example.test", _=object())

    assert alias_response.source == "alias@example.test"
    assert messages[0].to == "agent@example.test"
    assert message.id == "1"


def test_get_mailbox_message_returns_not_found(monkeypatch):
    monkeypatch.setattr(mailboxes, "get_message", lambda address, message_id: None)

    with pytest.raises(mailboxes.HTTPException, match="Message not found"):
        mailboxes.get_mailbox_message("1", "agent@example.test", _=object())

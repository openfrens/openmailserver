from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from openmailserver.api import mail
from openmailserver.models import Alias, Domain, Mailbox, OutboundMessage
from openmailserver.schemas import SendMailRequest


def test_send_mail_commits_and_serializes_record(db_session, monkeypatch):
    def fake_send_outbound_message(db, **kwargs):
        assert kwargs["authenticated_sender"] is None
        record = OutboundMessage(
            sender=kwargs["sender"],
            recipients=kwargs["recipients"],
            cc=kwargs["cc"],
            bcc=kwargs["bcc"],
            subject=kwargs["subject"],
            text_body=kwargs["text_body"],
            html_body=kwargs["html_body"],
            raw_mime="raw",
            state="sent",
        )
        db.add(record)
        db.flush()
        return record

    monkeypatch.setattr(mail, "send_outbound_message", fake_send_outbound_message)

    response = mail.send_mail(
        SendMailRequest(
            sender="agent@example.test",
            recipients=["person@example.test"],
            subject="Hello",
            text_body="World",
        ),
        db=db_session,
        api_key=SimpleNamespace(mailbox_id=None),
    )

    assert response.sender == "agent@example.test"
    assert response.recipients == ["person@example.test"]
    assert response.state == "sent"


def test_list_outbound_returns_newest_first(db_session):
    older = OutboundMessage(
        sender="agent@example.test",
        recipients=["one@example.test"],
        cc=[],
        bcc=[],
        subject="Older",
        raw_mime="raw",
        state="queued",
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    newer = OutboundMessage(
        sender="agent@example.test",
        recipients=["two@example.test"],
        cc=[],
        bcc=[],
        subject="Newer",
        raw_mime="raw",
        state="queued",
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
    )
    db_session.add_all([older, newer])
    db_session.commit()

    response = mail.list_outbound(db=db_session, _=object())

    assert [item.subject for item in response] == ["Newer", "Older"]


def test_get_outbound_and_attachment_errors(db_session):
    record = OutboundMessage(
        sender="agent@example.test",
        recipients=["reader@example.test"],
        cc=[],
        bcc=[],
        subject="Stored",
        raw_mime="raw",
        state="queued",
    )
    db_session.add(record)
    db_session.commit()

    response = mail.get_outbound(record.id, db=db_session, _=object())

    assert response.id == record.id

    with pytest.raises(mail.HTTPException, match="Outbound message not found"):
        mail.get_outbound(9999, db=db_session, _=object())

    with pytest.raises(mail.HTTPException, match="Attachment missing is not available"):
        mail.get_attachment("missing", _=object())


def test_mailbox_key_sender_restrictions_allow_mailbox_and_alias(db_session):
    domain = Domain(name="example.test")
    mailbox = Mailbox(
        domain=domain,
        local_part="agent",
        email="agent@example.test",
        runtime_account="agent-example-test",
        password_hash="hashed",
        maildir_path="/tmp/maildir",
    )
    db_session.add(mailbox)
    db_session.flush()
    db_session.add(Alias(source="alias@example.test", destination="agent@example.test"))
    db_session.commit()

    key = type("MailboxKey", (), {"mailbox_id": mailbox.id})()

    assert mail._allowed_senders(db_session, key) == {"agent@example.test", "alias@example.test"}
    assert mail._authenticated_sender(db_session, key) == "agent@example.test"


def test_mailbox_key_cannot_send_as_other_sender(db_session):
    domain = Domain(name="example.test")
    mailbox = Mailbox(
        domain=domain,
        local_part="agent",
        email="agent@example.test",
        runtime_account="agent-example-test",
        password_hash="hashed",
        maildir_path="/tmp/maildir",
    )
    db_session.add(mailbox)
    db_session.commit()

    key = type("MailboxKey", (), {"mailbox_id": mailbox.id})()

    with pytest.raises(mail.HTTPException, match="Sender is not permitted"):
        mail.send_mail(
            SendMailRequest(
                sender="other@example.test",
                recipients=["person@example.test"],
                subject="Hello",
                text_body="World",
            ),
            db=db_session,
            api_key=key,
        )

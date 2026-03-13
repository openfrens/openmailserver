from __future__ import annotations

from datetime import UTC, datetime

import pytest

from openmailserver.api import mail
from openmailserver.models import OutboundMessage
from openmailserver.schemas import SendMailRequest


def test_send_mail_commits_and_serializes_record(db_session, monkeypatch):
    def fake_send_outbound_message(db, **kwargs):
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
        _=object(),
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

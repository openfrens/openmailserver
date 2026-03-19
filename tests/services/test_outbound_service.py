from __future__ import annotations

from types import SimpleNamespace

from openmailserver.models import DeliveryEvent, Domain, Mailbox
from openmailserver.services import outbound_service


def test_build_message_creates_multipart_email():
    message = outbound_service.build_message(
        sender="agent@example.test",
        recipients=["reader@example.test"],
        subject="Hello",
        text_body="Plain",
        html_body="<b>HTML</b>",
        cc=["copy@example.test"],
        bcc=["blind@example.test"],
    )

    assert message["From"] == "agent@example.test"
    assert message["To"] == "reader@example.test"
    assert message["Cc"] == "copy@example.test"
    assert message["Message-Id"]
    assert message.is_multipart() is True


def test_send_outbound_message_sends_maildir_copy_and_records_event(
    db_session, monkeypatch
):
    settings = SimpleNamespace(
        transport_mode="maildir",
        smtp_host="127.0.0.1",
        smtp_port=25,
        smtp_timeout_seconds=15,
    )
    delivered = []

    domain = Domain(name="outbound.test")
    mailbox = Mailbox(
        domain=domain,
        local_part="agent",
        email="agent@outbound.test",
        password_hash="hashed",
        maildir_path="/tmp/maildir",
    )
    db_session.add_all([domain, mailbox])
    db_session.commit()

    monkeypatch.setattr(outbound_service, "get_settings", lambda: settings)
    monkeypatch.setattr(
        outbound_service,
        "deliver_local_copy",
        lambda email, raw_message: delivered.append(email) or "maildir-id",
    )
    monkeypatch.setattr(outbound_service, "write_system_log", lambda *args, **kwargs: None)

    record = outbound_service.send_outbound_message(
        db_session,
        sender="agent@outbound.test",
        recipients=["reader@outbound.test"],
        subject="Hello",
        text_body="World",
    )
    db_session.commit()

    events = db_session.query(DeliveryEvent).all()

    assert record.state == "sent"
    assert delivered == ["reader@outbound.test", "agent@outbound.test"]
    assert len(events) == 1
    assert events[0].event_type == "sent"


def test_send_outbound_message_marks_failures(db_session, monkeypatch):
    settings = SimpleNamespace(
        transport_mode="smtp",
        smtp_host="127.0.0.1",
        smtp_port=2525,
        smtp_timeout_seconds=5,
    )
    logs = []

    class _BrokenSMTP:
        def __init__(self, host, port, timeout):
            self.host = host
            self.port = port
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def send_message(self, message, from_addr, to_addrs):
            raise OSError("smtp unavailable")

    monkeypatch.setattr(outbound_service, "get_settings", lambda: settings)
    monkeypatch.setattr(outbound_service.smtplib, "SMTP", _BrokenSMTP)
    monkeypatch.setattr(outbound_service, "write_system_log", lambda *args, **kwargs: logs.append(args))

    record = outbound_service.send_outbound_message(
        db_session,
        sender="agent@example.test",
        recipients=["reader@example.test"],
        subject="Hello",
        text_body="World",
    )
    db_session.commit()

    assert record.state == "failed"
    assert record.error == "smtp unavailable"
    assert len(logs) == 2

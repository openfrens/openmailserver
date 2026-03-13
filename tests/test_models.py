from __future__ import annotations

from sqlalchemy.types import JSON

from openmailserver import models
from openmailserver.security import hash_api_key


def test_utcnow_returns_timezone_aware_datetime():
    now = models.utcnow()

    assert now.tzinfo is not None


def test_json_type_uses_json_column_type():
    assert isinstance(models.json_type(), JSON)


def test_model_relationships_round_trip(db_session):
    domain = models.Domain(name="example.test")
    db_session.add(domain)
    db_session.flush()

    mailbox = models.Mailbox(
        domain=domain,
        local_part="agent",
        email="agent@example.test",
        password_hash="hashed-password",
        maildir_path="/tmp/maildir",
        quota=2048,
    )
    api_key = models.ApiKey(
        name="mailbox-default",
        key_hash=hash_api_key("mailbox-default"),
        scopes=["mail:read"],
        mailbox=mailbox,
    )
    message = models.OutboundMessage(
        sender="agent@example.test",
        recipients=["agent@example.test"],
        cc=[],
        bcc=[],
        subject="Hello",
        text_body="world",
        raw_mime="raw",
        state="queued",
        debug_metadata={"source": "test"},
    )
    event = models.DeliveryEvent(message=message, event_type="queued", details={"queue_id": None})
    trusted_peer = models.TrustedPeer(
        instance_name="peer-a",
        domain="peer.example.test",
        public_key="ssh-rsa AAAA",
    )
    system_log = models.SystemLog(
        level="info",
        event_type="outbound_send",
        message="processed",
        payload={"message_id": 1},
    )

    db_session.add_all([mailbox, api_key, message, event, trusted_peer, system_log])
    db_session.commit()

    stored_mailbox = (
        db_session.query(models.Mailbox)
        .filter(models.Mailbox.email == "agent@example.test")
        .one()
    )
    stored_message = db_session.query(models.OutboundMessage).one()

    assert stored_mailbox.domain.name == "example.test"
    assert stored_mailbox.api_keys[0].name == "mailbox-default"
    assert stored_message.events[0].event_type == "queued"
    assert db_session.query(models.TrustedPeer).one().instance_name == "peer-a"
    assert db_session.query(models.SystemLog).one().event_type == "outbound_send"

from __future__ import annotations

from datetime import UTC, datetime

from openmailserver.models import DeliveryEvent, OutboundMessage
from openmailserver.services import queue_service


def test_list_queue_returns_messages_in_descending_order(db_session):
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
        state="sent",
        queue_id="queue-2",
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
    )
    db_session.add_all([older, newer])
    db_session.commit()

    queue = queue_service.list_queue(db_session)

    assert [item.id for item in queue] == [newer.id, older.id]


def test_message_trace_returns_events_and_missing_status(db_session):
    message = OutboundMessage(
        sender="agent@example.test",
        recipients=["one@example.test"],
        cc=[],
        bcc=[],
        subject="Traceable",
        raw_mime="raw",
        state="sent",
        message_id="msg-1",
        queue_id="queue-1",
    )
    db_session.add(message)
    db_session.flush()
    db_session.add(
        DeliveryEvent(
            outbound_message_id=message.id,
            event_type="sent",
            details={"queue_id": "queue-1"},
        )
    )
    db_session.commit()

    trace = queue_service.message_trace(db_session, message.id)
    missing = queue_service.message_trace(db_session, 9999)

    assert trace["status"] == "sent"
    assert trace["events"][0]["event_type"] == "sent"
    assert missing == {"status": "missing", "events": []}

from __future__ import annotations

from sqlalchemy.orm import Session

from openmailserver.models import DeliveryEvent, OutboundMessage


def list_queue(db: Session) -> list[dict]:
    messages = db.query(OutboundMessage).order_by(OutboundMessage.created_at.desc()).all()
    return [
        {
            "id": message.id,
            "state": message.state,
            "queue_id": message.queue_id,
            "message_id": message.message_id,
            "error": message.error,
            "created_at": message.created_at.isoformat(),
        }
        for message in messages
    ]


def message_trace(db: Session, outbound_message_id: int) -> dict:
    message = db.query(OutboundMessage).filter(OutboundMessage.id == outbound_message_id).first()
    if not message:
        return {"status": "missing", "events": []}
    events = (
        db.query(DeliveryEvent)
        .filter(DeliveryEvent.outbound_message_id == outbound_message_id)
        .all()
    )
    return {
        "status": message.state,
        "message_id": message.message_id,
        "queue_id": message.queue_id,
        "error": message.error,
        "events": [
            {
                "event_type": event.event_type,
                "details": event.details,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ],
    }

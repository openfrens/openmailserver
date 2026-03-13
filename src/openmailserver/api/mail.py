from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from openmailserver.deps import get_db, require_api_key
from openmailserver.models import OutboundMessage
from openmailserver.schemas import OutboundMessageRead, SendMailRequest
from openmailserver.security import MAIL_READ_SCOPE, MAIL_SEND_SCOPE
from openmailserver.services.outbound_service import send_outbound_message

router = APIRouter()


@router.post("/mail/send", response_model=OutboundMessageRead)
def send_mail(
    payload: SendMailRequest,
    db: Session = Depends(get_db),
    _: object = Depends(require_api_key(MAIL_SEND_SCOPE)),
) -> OutboundMessageRead:
    record = send_outbound_message(
        db,
        sender=str(payload.sender),
        recipients=[str(item) for item in payload.recipients],
        subject=payload.subject,
        text_body=payload.text_body,
        html_body=payload.html_body,
        cc=[str(item) for item in payload.cc],
        bcc=[str(item) for item in payload.bcc],
    )
    db.commit()
    db.refresh(record)
    return OutboundMessageRead.model_validate(record)


@router.get("/outbound", response_model=list[OutboundMessageRead])
def list_outbound(
    db: Session = Depends(get_db),
    _: object = Depends(require_api_key(MAIL_READ_SCOPE)),
) -> list[OutboundMessageRead]:
    records = db.query(OutboundMessage).order_by(OutboundMessage.created_at.desc()).all()
    return [OutboundMessageRead.model_validate(record) for record in records]


@router.get("/outbound/{outbound_id}", response_model=OutboundMessageRead)
def get_outbound(
    outbound_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_api_key(MAIL_READ_SCOPE)),
) -> OutboundMessageRead:
    record = db.query(OutboundMessage).filter(OutboundMessage.id == outbound_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Outbound message not found")
    return OutboundMessageRead.model_validate(record)


@router.get("/attachments/{attachment_id}", response_model=dict)
def get_attachment(
    attachment_id: str,
    _: object = Depends(require_api_key(MAIL_READ_SCOPE)),
) -> dict:
    detail = f"Attachment {attachment_id} is not available in this build"
    raise HTTPException(status_code=404, detail=detail)

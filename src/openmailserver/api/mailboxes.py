from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from openmailserver.deps import get_db, require_api_key
from openmailserver.schemas import (
    AliasCreate,
    AliasRead,
    MailboxCreate,
    MailboxMessageRead,
    MailboxMessageSummary,
    MailboxProvisionResponse,
)
from openmailserver.security import ADMIN_SCOPE, MAIL_READ_SCOPE
from openmailserver.services.domain_service import DomainNotReadyError
from openmailserver.services.mailbox_service import (
    MailboxExistsError,
    create_alias_record,
    provision_mailbox,
)
from openmailserver.services.maildir_service import get_message, list_messages

router = APIRouter()


@router.post("/mailboxes", response_model=MailboxProvisionResponse)
def create_mailbox(
    payload: MailboxCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_api_key(ADMIN_SCOPE)),
) -> MailboxProvisionResponse:
    try:
        return provision_mailbox(db, payload)
    except (MailboxExistsError, DomainNotReadyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/aliases", response_model=AliasRead)
def create_alias(
    payload: AliasCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_api_key(ADMIN_SCOPE)),
) -> AliasRead:
    return create_alias_record(db, payload)


@router.get("/mailboxes/{address}/messages", response_model=list[MailboxMessageSummary])
def get_mailbox_messages(
    address: str,
    _: object = Depends(require_api_key(MAIL_READ_SCOPE)),
) -> list[MailboxMessageSummary]:
    return list_messages(address)


@router.get("/messages/{message_id}", response_model=MailboxMessageRead)
def get_mailbox_message(
    message_id: str,
    address: str,
    _: object = Depends(require_api_key(MAIL_READ_SCOPE)),
) -> MailboxMessageRead:
    message = get_message(address, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    return message

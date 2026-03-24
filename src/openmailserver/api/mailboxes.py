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
from openmailserver.services.mailbox_reader_service import (
    MailboxReadError,
    get_message,
    list_messages,
)
from openmailserver.services.mailbox_service import (
    MailboxExistsError,
    create_alias_record,
    provision_mailbox,
)
from openmailserver.services.mox_service import MoxRuntimeNotReadyError, MoxSyncError

router = APIRouter()


def _raise_mox_http(db: Session, exc: MoxSyncError) -> None:
    db.rollback()
    status_code = 503 if isinstance(exc, MoxRuntimeNotReadyError) else 400
    raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post("/mailboxes", response_model=MailboxProvisionResponse)
def create_mailbox(
    payload: MailboxCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_api_key(ADMIN_SCOPE)),
) -> MailboxProvisionResponse:
    try:
        return provision_mailbox(db, payload)
    except MailboxExistsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except MoxSyncError as exc:
        _raise_mox_http(db, exc)


@router.post("/aliases", response_model=AliasRead)
def create_alias(
    payload: AliasCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_api_key(ADMIN_SCOPE)),
) -> AliasRead:
    try:
        return create_alias_record(db, payload)
    except MoxSyncError as exc:
        _raise_mox_http(db, exc)


@router.get("/mailboxes/{address}/messages", response_model=list[MailboxMessageSummary])
def get_mailbox_messages(
    address: str,
    _: object = Depends(require_api_key(MAIL_READ_SCOPE)),
) -> list[MailboxMessageSummary]:
    try:
        return list_messages(address)
    except MailboxReadError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/messages/{message_id}", response_model=MailboxMessageRead)
def get_mailbox_message(
    message_id: str,
    address: str,
    _: object = Depends(require_api_key(MAIL_READ_SCOPE)),
) -> MailboxMessageRead:
    try:
        message = get_message(address, message_id)
    except MailboxReadError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    return message

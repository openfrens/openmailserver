from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from openmailserver.deps import get_db, require_api_key
from openmailserver.models import Alias, Domain, Mailbox
from openmailserver.schemas import AliasCreate, ApiKeyResponse, MailboxCreate, MailboxRead
from openmailserver.security import generate_api_key, generate_secret, hash_mailbox_password
from openmailserver.services.maildir_service import ensure_maildir, get_message, list_messages

router = APIRouter()


@router.post("/mailboxes", response_model=dict)
def create_mailbox(
    payload: MailboxCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_api_key("admin")),
) -> dict:
    domain = db.query(Domain).filter(Domain.name == payload.domain).first()
    if not domain:
        domain = Domain(name=payload.domain)
        db.add(domain)
        db.flush()

    email = f"{payload.local_part}@{payload.domain}"
    if db.query(Mailbox).filter(Mailbox.email == email).first():
        raise HTTPException(status_code=400, detail="Mailbox already exists")

    password = payload.password or generate_secret(18)
    maildir_path = str(ensure_maildir(email))
    mailbox = Mailbox(
        domain_id=domain.id,
        local_part=payload.local_part,
        email=email,
        password_hash=hash_mailbox_password(password),
        maildir_path=maildir_path,
        quota=payload.quota,
    )
    db.add(mailbox)
    key = generate_api_key(prefix="mailbox")
    from openmailserver.models import ApiKey

    api_key = ApiKey(
        name=f"{email}-default",
        key_hash=key.hashed_key,
        scopes=["mail:read", "mail:send", "debug:read"],
        mailbox=mailbox,
    )
    db.add(api_key)
    db.commit()
    return {
        "mailbox": MailboxRead.model_validate(mailbox).model_dump(),
        "password": password,
        "api_key": ApiKeyResponse(key=key.raw_key, scopes=api_key.scopes).model_dump(),
    }


@router.post("/aliases", response_model=dict)
def create_alias(
    payload: AliasCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_api_key("admin")),
) -> dict:
    alias = Alias(source=str(payload.source), destination=str(payload.destination))
    db.add(alias)
    db.commit()
    return {"id": alias.id, "source": alias.source, "destination": alias.destination}


@router.get("/mailboxes/{address}/messages", response_model=list[dict])
def get_mailbox_messages(
    address: str,
    _: object = Depends(require_api_key("mail:read")),
) -> list[dict]:
    return list_messages(address)


@router.get("/messages/{message_id}", response_model=dict)
def get_mailbox_message(
    message_id: str,
    address: str,
    _: object = Depends(require_api_key("mail:read")),
) -> dict:
    message = get_message(address, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    return message

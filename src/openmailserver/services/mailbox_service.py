from __future__ import annotations

from sqlalchemy.orm import Session

from openmailserver.models import Alias, ApiKey, Mailbox
from openmailserver.schemas import (
    AliasCreate,
    AliasRead,
    ApiKeyResponse,
    MailboxCreate,
    MailboxProvisionResponse,
    MailboxRead,
)
from openmailserver.security import (
    DEFAULT_MAILBOX_SCOPES,
    generate_api_key,
    generate_secret,
    hash_mailbox_password,
)
from openmailserver.services.maildir_service import ensure_maildir
from openmailserver.services.mox_service import (
    mailbox_runtime_account,
    resolve_or_create_domain,
    set_mailbox_runtime_password,
    split_address,
    sync_alias_to_mox,
    sync_mailbox_to_mox,
)
from openmailserver.services.runtime_secret_service import store_mailbox_password


class MailboxExistsError(ValueError):
    pass


class MailboxNotFoundError(ValueError):
    pass


def provision_mailbox(db: Session, payload: MailboxCreate) -> MailboxProvisionResponse:
    domain = resolve_or_create_domain(db, payload.domain)

    email = f"{payload.local_part}@{payload.domain}"
    if db.query(Mailbox).filter(Mailbox.email == email).first():
        raise MailboxExistsError("Mailbox already exists")

    password = payload.password or generate_secret(18)
    mailbox = Mailbox(
        domain_id=domain.id,
        local_part=payload.local_part,
        email=email,
        runtime_account=mailbox_runtime_account(payload.local_part, payload.domain),
        password_hash=hash_mailbox_password(password),
        maildir_path=str(ensure_maildir(email)),
        quota=payload.quota,
    )
    db.add(mailbox)

    key = generate_api_key(prefix="mailbox")
    api_key = ApiKey(
        name=f"{email}-default",
        key_hash=key.hashed_key,
        scopes=list(DEFAULT_MAILBOX_SCOPES),
        mailbox=mailbox,
    )
    db.add(api_key)
    db.flush()
    sync_mailbox_to_mox(db, mailbox, password)
    store_mailbox_password(email, password)
    db.commit()

    return MailboxProvisionResponse(
        mailbox=MailboxRead.model_validate(mailbox),
        password=password,
        api_key=ApiKeyResponse(key=key.raw_key, scopes=api_key.scopes),
    )


def create_alias_record(db: Session, payload: AliasCreate) -> AliasRead:
    _, source_domain = split_address(str(payload.source))
    resolve_or_create_domain(db, source_domain)
    alias = Alias(source=str(payload.source), destination=str(payload.destination))
    db.add(alias)
    db.flush()
    sync_alias_to_mox(db, alias)
    db.commit()
    return AliasRead(id=alias.id, source=alias.source, destination=alias.destination)


def set_mailbox_password(db: Session, email: str, password: str) -> MailboxProvisionResponse:
    mailbox = db.query(Mailbox).filter(Mailbox.email == email).first()
    if mailbox is None:
        raise MailboxNotFoundError("Mailbox does not exist")
    mailbox.password_hash = hash_mailbox_password(password)
    set_mailbox_runtime_password(mailbox, password)
    store_mailbox_password(mailbox.email, password)
    db.commit()
    db.refresh(mailbox)
    return MailboxProvisionResponse(
        mailbox=MailboxRead.model_validate(mailbox),
        password=password,
        api_key=ApiKeyResponse(key="", scopes=[]),
    )

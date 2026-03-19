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
from openmailserver.services.domain_service import ensure_domain_ready
from openmailserver.services.maildir_service import ensure_maildir


class MailboxExistsError(ValueError):
    pass


def provision_mailbox(db: Session, payload: MailboxCreate) -> MailboxProvisionResponse:
    domain = ensure_domain_ready(db, payload.domain)

    email = f"{payload.local_part}@{payload.domain}"
    if db.query(Mailbox).filter(Mailbox.email == email).first():
        raise MailboxExistsError("Mailbox already exists")

    password = payload.password or generate_secret(18)
    mailbox = Mailbox(
        domain_id=domain.id,
        local_part=payload.local_part,
        email=email,
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
    db.commit()

    return MailboxProvisionResponse(
        mailbox=MailboxRead.model_validate(mailbox),
        password=password,
        api_key=ApiKeyResponse(key=key.raw_key, scopes=api_key.scopes),
    )


def create_alias_record(db: Session, payload: AliasCreate) -> AliasRead:
    alias = Alias(source=str(payload.source), destination=str(payload.destination))
    db.add(alias)
    db.commit()
    return AliasRead(id=alias.id, source=alias.source, destination=alias.destination)

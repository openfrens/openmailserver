from __future__ import annotations

import io
import json
import tarfile
from datetime import UTC, datetime
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.orm import Session

from openmailserver.config import get_settings
from openmailserver.models import (
    Alias,
    ApiKey,
    DeliveryEvent,
    Domain,
    Mailbox,
    OutboundMessage,
    TrustedPeer,
)


def _fernet() -> Fernet:
    settings = get_settings()
    key = settings.backup_encryption_key
    if not key:
        raise ValueError("OPENMAILSERVER_BACKUP_ENCRYPTION_KEY must be configured")
    return Fernet(key.encode("utf-8"))


def _dump_table(db: Session, model) -> list[dict]:
    records = db.execute(select(model)).scalars().all()
    return [
        {column.name: getattr(record, column.name) for column in model.__table__.columns}
        for record in records
    ]


def create_backup(db: Session) -> Path:
    settings = get_settings()
    payload = {
        "domains": _dump_table(db, Domain),
        "mailboxes": _dump_table(db, Mailbox),
        "aliases": _dump_table(db, Alias),
        "api_keys": _dump_table(db, ApiKey),
        "outbound_messages": _dump_table(db, OutboundMessage),
        "delivery_events": _dump_table(db, DeliveryEvent),
        "trusted_peers": _dump_table(db, TrustedPeer),
        "created_at": datetime.now(UTC).isoformat(),
    }

    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as archive:
        db_blob = json.dumps(payload, default=str).encode("utf-8")
        info = tarfile.TarInfo("database.json")
        info.size = len(db_blob)
        archive.addfile(info, io.BytesIO(db_blob))

        for folder_name in ["maildir", "attachments"]:
            folder = settings.data_dir / folder_name
            if folder.exists():
                archive.add(folder, arcname=folder_name)

    encrypted = _fernet().encrypt(tar_buffer.getvalue())
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    backup_path = settings.backup_dir / f"openmailserver-backup-{stamp}.tar.gz.enc"
    backup_path.write_bytes(encrypted)
    return backup_path


def validate_backup(path: Path) -> dict:
    try:
        data = _fernet().decrypt(path.read_bytes())
    except InvalidToken as exc:
        return {"status": "invalid", "reason": str(exc)}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        names = archive.getnames()
    return {"status": "ok", "entries": names}


def restore_backup(db: Session, path: Path) -> dict:
    settings = get_settings()
    data = _fernet().decrypt(path.read_bytes())
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        database_member = archive.extractfile("database.json")
        if database_member is None:
            raise ValueError("database.json missing from backup")
        payload = json.loads(database_member.read().decode("utf-8"))
        archive.extractall(settings.data_dir)

    for model in [DeliveryEvent, OutboundMessage, ApiKey, Alias, Mailbox, Domain, TrustedPeer]:
        db.query(model).delete()
    db.commit()

    def load(model, entries: list[dict]) -> None:
        for entry in entries:
            db.add(model(**entry))

    load(Domain, payload.get("domains", []))
    load(Mailbox, payload.get("mailboxes", []))
    load(Alias, payload.get("aliases", []))
    load(ApiKey, payload.get("api_keys", []))
    load(OutboundMessage, payload.get("outbound_messages", []))
    load(DeliveryEvent, payload.get("delivery_events", []))
    load(TrustedPeer, payload.get("trusted_peers", []))
    db.commit()
    return {"status": "ok", "restored_at": payload.get("created_at")}

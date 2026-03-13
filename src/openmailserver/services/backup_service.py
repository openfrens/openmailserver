from __future__ import annotations

import io
import json
import tarfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import DateTime, select
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

_ALLOWED_BACKUP_ROOTS = {"database.json", "maildir", "attachments"}


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


def _restore_entry(model, entry: dict) -> dict:
    restored = {}
    for column in model.__table__.columns:
        if column.name not in entry:
            continue
        value = entry[column.name]
        if isinstance(value, str) and isinstance(column.type, DateTime):
            value = datetime.fromisoformat(value)
        restored[column.name] = value
    return restored


def _validated_members(archive: tarfile.TarFile) -> list[tarfile.TarInfo]:
    members = archive.getmembers()
    safe_members: list[tarfile.TarInfo] = []
    for member in members:
        relative_path = PurePosixPath(member.name)
        if not member.name:
            raise ValueError("Backup contains an empty archive member")
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError(f"Backup contains unsafe path: {member.name}")
        if relative_path.parts[0] not in _ALLOWED_BACKUP_ROOTS:
            raise ValueError(f"Backup contains unexpected path: {member.name}")
        if relative_path.parts[0] == "database.json" and len(relative_path.parts) != 1:
            raise ValueError("database.json must remain a top-level archive entry")
        if member.issym() or member.islnk():
            raise ValueError(f"Backup contains unsupported link entry: {member.name}")
        if not member.isdir() and not member.isfile():
            raise ValueError(f"Backup contains unsupported archive member: {member.name}")
        safe_members.append(member)
    return safe_members


def _extract_members(
    archive: tarfile.TarFile, destination_root: Path, members: list[tarfile.TarInfo]
) -> None:
    for member in members:
        relative_path = PurePosixPath(member.name)
        target_path = destination_root.joinpath(*relative_path.parts)
        if member.isdir():
            target_path.mkdir(parents=True, exist_ok=True)
            continue

        extracted = archive.extractfile(member)
        if extracted is None:
            raise ValueError(f"Unable to read archived file: {member.name}")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(extracted.read())


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
        try:
            members = _validated_members(archive)
        except ValueError as exc:
            return {"status": "invalid", "reason": str(exc)}
        names = [member.name for member in members]
    return {"status": "ok", "entries": names}


def restore_backup(db: Session, path: Path) -> dict:
    settings = get_settings()
    data = _fernet().decrypt(path.read_bytes())
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        members = _validated_members(archive)
        database_info = next((member for member in members if member.name == "database.json"), None)
        if database_info is None:
            raise ValueError("database.json missing from backup")
        database_member = archive.extractfile(database_info)
        if database_member is None:
            raise ValueError("database.json is unreadable in backup")
        payload = json.loads(database_member.read().decode("utf-8"))
        content_members = [member for member in members if member.name != "database.json"]
        _extract_members(archive, settings.data_dir, content_members)

    for model in [DeliveryEvent, OutboundMessage, ApiKey, Alias, Mailbox, Domain, TrustedPeer]:
        db.query(model).delete()
    db.commit()

    def load(model, entries: list[dict]) -> None:
        for entry in entries:
            db.add(model(**_restore_entry(model, entry)))

    load(Domain, payload.get("domains", []))
    load(Mailbox, payload.get("mailboxes", []))
    load(Alias, payload.get("aliases", []))
    load(ApiKey, payload.get("api_keys", []))
    load(OutboundMessage, payload.get("outbound_messages", []))
    load(DeliveryEvent, payload.get("delivery_events", []))
    load(TrustedPeer, payload.get("trusted_peers", []))
    db.commit()
    return {"status": "ok", "restored_at": payload.get("created_at")}

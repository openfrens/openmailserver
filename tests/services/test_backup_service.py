from __future__ import annotations

import io
import tarfile
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet

from openmailserver.models import (
    Alias,
    ApiKey,
    DeliveryEvent,
    Domain,
    Mailbox,
    OutboundMessage,
    TrustedPeer,
)
from openmailserver.security import hash_api_key
from openmailserver.services import backup_service


def test_create_validate_and_restore_backup(db_session, monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    backup_dir = tmp_path / "backups"
    config_root = tmp_path / "runtime"
    (data_dir / "maildir").mkdir(parents=True)
    (data_dir / "attachments").mkdir(parents=True)
    (data_dir / "attachments" / "note.txt").write_text("payload", encoding="utf-8")
    (config_root / "mox" / "config").mkdir(parents=True)
    (config_root / "mox" / "data").mkdir(parents=True)
    (config_root / "mox" / "web").mkdir(parents=True)
    (config_root / "mox" / "config" / "mox.conf").write_text("config", encoding="utf-8")
    (config_root / "mox" / "data" / "mailbox.db").write_text("maildata", encoding="utf-8")
    (config_root / "mox" / "web" / "index.html").write_text("web", encoding="utf-8")
    runtime_secret_path = config_root / "secrets.json"
    runtime_secret_path.write_text("{}", encoding="utf-8")
    backup_dir.mkdir(parents=True)
    settings = SimpleNamespace(
        data_dir=data_dir,
        backup_dir=backup_dir,
        backup_encryption_key=Fernet.generate_key().decode("utf-8"),
        maildir_root=data_dir / "maildir",
        attachment_root=data_dir / "attachments",
        mox_config_dir=config_root / "mox" / "config",
        mox_data_dir=config_root / "mox" / "data",
        mox_web_dir=config_root / "mox" / "web",
        runtime_secret_path=runtime_secret_path,
    )
    monkeypatch.setattr(backup_service, "get_settings", lambda: settings)

    domain = Domain(name="example.test")
    mailbox = Mailbox(
        domain=domain,
        local_part="agent",
        email="agent@example.test",
        runtime_account="agent-example-test",
        password_hash="hashed",
        maildir_path=str(data_dir / "maildir" / "example.test" / "agent"),
    )
    alias = Alias(source="alias@example.test", destination="agent@example.test")
    api_key = ApiKey(
        name="default",
        key_hash=hash_api_key("raw-api-key"),
        scopes=["admin"],
        mailbox=mailbox,
    )
    message = OutboundMessage(
        sender="agent@example.test",
        recipients=["reader@example.test"],
        cc=[],
        bcc=[],
        subject="Backup me",
        raw_mime="raw",
        state="sent",
        debug_metadata={"source": "test"},
    )
    trusted_peer = TrustedPeer(
        instance_name="peer-a",
        domain="peer.example.test",
        public_key="ssh-rsa AAAA",
    )

    db_session.add_all([domain, mailbox, alias, api_key, message, trusted_peer])
    db_session.flush()
    db_session.add(
        DeliveryEvent(
            outbound_message_id=message.id,
            event_type="sent",
            details={"queue_id": None},
        )
    )
    db_session.commit()

    backup_path = backup_service.create_backup(db_session)
    validation = backup_service.validate_backup(backup_path)
    restore = backup_service.restore_backup(db_session, backup_path)

    assert backup_path.exists()
    assert validation["status"] == "ok"
    assert "database.json" in validation["entries"]
    assert "mox-config/mox.conf" in validation["entries"]
    assert "mox-data/mailbox.db" in validation["entries"]
    assert "mox-web/index.html" in validation["entries"]
    assert "runtime-secrets.json" in validation["entries"]
    assert restore["status"] == "ok"
    assert db_session.query(Domain).filter(Domain.name == "example.test").count() == 1
    assert db_session.query(OutboundMessage).one().subject == "Backup me"
    assert (data_dir / "attachments" / "note.txt").exists()
    assert (config_root / "mox" / "config" / "mox.conf").read_text(encoding="utf-8") == "config"
    assert (config_root / "mox" / "data" / "mailbox.db").read_text(encoding="utf-8") == "maildata"
    assert (config_root / "mox" / "web" / "index.html").read_text(encoding="utf-8") == "web"
    assert runtime_secret_path.read_text(encoding="utf-8") == "{}"


def test_backup_validation_rejects_path_traversal_archive(db_session, monkeypatch, tmp_path):
    data_dir = tmp_path / "data"
    backup_dir = tmp_path / "backups"
    data_dir.mkdir(parents=True)
    backup_dir.mkdir(parents=True)
    settings = SimpleNamespace(
        data_dir=data_dir,
        backup_dir=backup_dir,
        backup_encryption_key=Fernet.generate_key().decode("utf-8"),
        maildir_root=data_dir / "maildir",
        attachment_root=data_dir / "attachments",
        mox_config_dir=tmp_path / "runtime" / "mox" / "config",
        mox_data_dir=tmp_path / "runtime" / "mox" / "data",
        mox_web_dir=tmp_path / "runtime" / "mox" / "web",
        runtime_secret_path=tmp_path / "runtime" / "secrets.json",
    )
    monkeypatch.setattr(backup_service, "get_settings", lambda: settings)

    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w:gz") as archive:
        db_blob = b"{}"
        db_info = tarfile.TarInfo("database.json")
        db_info.size = len(db_blob)
        archive.addfile(db_info, io.BytesIO(db_blob))

        payload = b"owned"
        evil_info = tarfile.TarInfo("../owned.txt")
        evil_info.size = len(payload)
        archive.addfile(evil_info, io.BytesIO(payload))

    encrypted = backup_service._fernet().encrypt(tar_buffer.getvalue())
    backup_path = backup_dir / "malicious.tar.gz.enc"
    backup_path.write_bytes(encrypted)

    validation = backup_service.validate_backup(backup_path)

    assert validation["status"] == "invalid"
    assert "unsafe path" in validation["reason"]

    with pytest.raises(ValueError, match="unsafe path"):
        backup_service.restore_backup(db_session, backup_path)

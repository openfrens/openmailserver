from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("OPENMAILSERVER_DATABASE_URL", "sqlite+pysqlite:///./tests/runtime/test.sqlite3")
os.environ.setdefault("OPENMAILSERVER_FALLBACK_DATABASE_URL", "sqlite+pysqlite:///./tests/runtime/test.sqlite3")
os.environ.setdefault("OPENMAILSERVER_DATA_DIR", "./tests/runtime/data")
os.environ.setdefault("OPENMAILSERVER_LOG_DIR", "./tests/runtime/logs")
os.environ.setdefault("OPENMAILSERVER_MAILDIR_ROOT", "./tests/runtime/maildir")
os.environ.setdefault("OPENMAILSERVER_ATTACHMENT_ROOT", "./tests/runtime/attachments")
os.environ.setdefault("OPENMAILSERVER_CONFIG_ROOT", "./tests/runtime/config")
os.environ.setdefault("OPENMAILSERVER_LOG_FILE", "./tests/runtime/logs/openmailserver.log")
os.environ.setdefault("OPENMAILSERVER_TRANSPORT_MODE", "maildir")
os.environ.setdefault("OPENMAILSERVER_PRIMARY_DOMAIN", "example.test")
os.environ.setdefault("OPENMAILSERVER_CANONICAL_HOSTNAME", "mail.example.test")
os.environ.setdefault("OPENMAILSERVER_PUBLIC_IP", "127.0.0.1")
os.environ.setdefault("OPENMAILSERVER_MOX_BINARY", "mox")
os.environ.setdefault("OPENMAILSERVER_MOX_ADMIN_ACCOUNT", "admin")
os.environ.setdefault("OPENMAILSERVER_MOX_ADMIN_ADDRESS", "admin@example.test")
os.environ.setdefault("OPENMAILSERVER_ADMIN_API_KEY", "test-admin-key")
os.environ.setdefault(
    "OPENMAILSERVER_BACKUP_ENCRYPTION_KEY",
    "MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI=",
)

import pytest
from fastapi.testclient import TestClient

from openmailserver.app import app
from openmailserver.database import Base, SessionLocal, get_engine
from openmailserver.models import ApiKey
from openmailserver.security import hash_api_key
from openmailserver.services import mailbox_service


@pytest.fixture(autouse=True)
def reset_database():
    runtime = Path("./tests/runtime")
    runtime.mkdir(parents=True, exist_ok=True)
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    session.add(
        ApiKey(
            name="test-admin",
            key_hash=hash_api_key("test-admin-key"),
            scopes=["admin", "debug:read", "mail:read", "mail:send"],
        )
    )
    session.commit()
    session.close()
    yield


@pytest.fixture(autouse=True)
def stub_mox_sync(monkeypatch):
    monkeypatch.setattr(mailbox_service, "sync_mailbox_to_mox", lambda db, mailbox, password: None)
    monkeypatch.setattr(mailbox_service, "sync_alias_to_mox", lambda db, alias: None)


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def admin_headers() -> dict[str, str]:
    return {"X-OpenMailserver-Key": "test-admin-key"}

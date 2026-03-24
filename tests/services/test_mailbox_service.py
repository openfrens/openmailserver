from __future__ import annotations

from pathlib import Path

import pytest

from openmailserver.models import Alias, Domain, Mailbox
from openmailserver.schemas import AliasCreate, MailboxCreate
from openmailserver.security import GeneratedApiKey, verify_mailbox_password
from openmailserver.services import mailbox_service


def test_provision_mailbox_creates_domain_mailbox_and_api_key(db_session, monkeypatch):
    stored_passwords = {}
    monkeypatch.setattr(mailbox_service, "ensure_maildir", lambda email: Path("/tmp") / email)
    monkeypatch.setattr(mailbox_service, "sync_mailbox_to_mox", lambda db, mailbox, password: None)
    monkeypatch.setattr(
        mailbox_service,
        "store_mailbox_password",
        lambda email, password: stored_passwords.setdefault(email, password),
    )
    monkeypatch.setattr(
        mailbox_service,
        "generate_api_key",
        lambda prefix="mailbox": GeneratedApiKey("mailbox_raw", "mailbox_hash"),
    )

    response = mailbox_service.provision_mailbox(
        db_session,
        MailboxCreate(local_part="agent", domain="example.test", password="secret-pass", quota=256),
    )

    stored_mailbox = db_session.query(Mailbox).filter(Mailbox.email == "agent@example.test").one()
    stored_domain = db_session.query(Domain).filter(Domain.name == "example.test").one()

    assert stored_domain.id == stored_mailbox.domain_id
    assert stored_mailbox.runtime_account == "agent-example-test"
    assert verify_mailbox_password("secret-pass", stored_mailbox.password_hash) is True
    assert response.mailbox.email == "agent@example.test"
    assert response.api_key.key == "mailbox_raw"
    assert stored_passwords == {"agent@example.test": "secret-pass"}


def test_provision_mailbox_rejects_duplicate_address(db_session, monkeypatch):
    monkeypatch.setattr(mailbox_service, "ensure_maildir", lambda email: Path("/tmp") / email)
    monkeypatch.setattr(mailbox_service, "sync_mailbox_to_mox", lambda db, mailbox, password: None)
    monkeypatch.setattr(mailbox_service, "store_mailbox_password", lambda email, password: None)
    monkeypatch.setattr(
        mailbox_service,
        "generate_api_key",
        lambda prefix="mailbox": GeneratedApiKey("mailbox_raw", "mailbox_hash"),
    )

    payload = MailboxCreate(local_part="agent", domain="example.test", password="secret-pass")
    mailbox_service.provision_mailbox(db_session, payload)

    with pytest.raises(mailbox_service.MailboxExistsError, match="Mailbox already exists"):
        mailbox_service.provision_mailbox(db_session, payload)


def test_create_alias_record_persists_alias(db_session, monkeypatch):
    mailbox = Mailbox(
        domain=Domain(name="example.test"),
        local_part="agent",
        email="agent@example.test",
        runtime_account="agent-example-test",
        password_hash="hashed",
        maildir_path="/tmp/agent",
    )
    db_session.add(mailbox)
    db_session.commit()
    monkeypatch.setattr(mailbox_service, "sync_alias_to_mox", lambda db, alias: None)
    alias = mailbox_service.create_alias_record(
        db_session,
        AliasCreate(source="alias@example.test", destination="agent@example.test"),
    )

    assert alias.source == "alias@example.test"
    assert db_session.query(Alias).one().destination == "agent@example.test"


def test_set_mailbox_password_updates_hash_runtime_and_secret(db_session, monkeypatch):
    stored_passwords = {}
    runtime_updates = []
    mailbox = Mailbox(
        domain=Domain(name="example.test"),
        local_part="agent",
        email="agent@example.test",
        runtime_account="agent-example-test",
        password_hash="old",
        maildir_path="/tmp/agent",
    )
    db_session.add(mailbox)
    db_session.commit()
    monkeypatch.setattr(
        mailbox_service,
        "set_mailbox_runtime_password",
        lambda mailbox, password: runtime_updates.append((mailbox.email, password)),
    )
    monkeypatch.setattr(
        mailbox_service,
        "store_mailbox_password",
        lambda email, password: stored_passwords.setdefault(email, password),
    )

    response = mailbox_service.set_mailbox_password(db_session, "agent@example.test", "new-pass")

    db_session.refresh(mailbox)
    assert verify_mailbox_password("new-pass", mailbox.password_hash) is True
    assert runtime_updates == [("agent@example.test", "new-pass")]
    assert stored_passwords == {"agent@example.test": "new-pass"}
    assert response.mailbox.email == "agent@example.test"


def test_set_mailbox_password_rejects_missing_mailbox(db_session):
    with pytest.raises(mailbox_service.MailboxNotFoundError, match="Mailbox does not exist"):
        mailbox_service.set_mailbox_password(db_session, "missing@example.test", "new-pass")

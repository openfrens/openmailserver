from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from openmailserver.models import Alias, Domain, Mailbox
from openmailserver.services import mox_service


def _settings(tmp_path: Path):
    mox_root = tmp_path / "runtime" / "mox"
    config_dir = mox_root / "config"
    data_dir = mox_root / "data"
    config_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "mox.conf").write_text("ok", encoding="utf-8")
    return SimpleNamespace(
        config_root=tmp_path / "runtime",
        canonical_hostname="mail.example.test",
        mox_binary="mox",
        mox_root=mox_root,
        mox_config_dir=config_dir,
        mox_data_dir=data_dir,
        mox_admin_account="admin",
        effective_mox_admin_address="admin@example.test",
    )


def test_runtime_account_name_is_stable():
    assert mox_service.runtime_account_name("Agent", "Example.TEST") == "agent-example-test"


def test_provision_mailbox_runs_domain_account_and_password_commands(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    calls = []
    mailbox = Mailbox(
        domain=Domain(name="example.test"),
        local_part="agent",
        email="agent@example.test",
        runtime_account="agent-example-test",
        password_hash="hashed",
        maildir_path="/tmp/maildir",
    )

    monkeypatch.setattr(mox_service.shutil, "which", lambda command: "/usr/local/bin/mox")

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mox_service.subprocess, "run", fake_run)

    service = mox_service.MoxSyncService(settings)
    service.provision_mailbox(mailbox, "secret-pass")

    assert calls[0][0][:4] == ["mox", "config", "domain", "add"]
    assert calls[1][0][:4] == ["mox", "config", "account", "add"]
    assert calls[2][0][:2] == ["mox", "setaccountpassword"]
    assert calls[2][1]["input"] == "secret-pass\nsecret-pass\n"
    assert calls[0][1]["env"]["MOXCONF"] == str((settings.mox_config_dir / "mox.conf").resolve())


def test_provision_alias_rejects_external_destinations(monkeypatch, tmp_path, db_session):
    settings = _settings(tmp_path)
    monkeypatch.setattr(mox_service.shutil, "which", lambda command: "/usr/local/bin/mox")

    alias = Alias(source="hello@example.test", destination="user@gmail.com")

    service = mox_service.MoxSyncService(settings)

    with pytest.raises(
        mox_service.ExternalAliasNotSupportedError,
        match="External forwarding aliases are not supported",
    ):
        service.provision_alias(db_session, alias)


def test_provision_alias_syncs_local_destinations(monkeypatch, tmp_path, db_session):
    settings = _settings(tmp_path)
    calls = []
    domain = Domain(name="example.test")
    mailbox = Mailbox(
        domain=domain,
        local_part="agent",
        email="agent@example.test",
        runtime_account="agent-example-test",
        password_hash="hashed",
        maildir_path="/tmp/maildir",
    )
    db_session.add(mailbox)
    db_session.commit()
    alias = Alias(source="hello@example.test", destination="agent@example.test")

    monkeypatch.setattr(mox_service.shutil, "which", lambda command: "/usr/local/bin/mox")

    def fake_run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mox_service.subprocess, "run", fake_run)

    service = mox_service.MoxSyncService(settings)
    service.provision_alias(db_session, alias)

    assert calls[0][:4] == ["mox", "config", "domain", "add"]
    assert calls[1][:4] == ["mox", "config", "alias", "add"]
    assert calls[2][:4] == ["mox", "config", "alias", "update"]
    assert calls[2][-2:] == ["-allowmsgfrom", "true"]


def test_runtime_ready_requires_initialized_mox(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    (settings.mox_config_dir / "mox.conf").unlink()
    monkeypatch.setattr(mox_service.shutil, "which", lambda command: "/usr/local/bin/mox")

    service = mox_service.MoxSyncService(settings)

    with pytest.raises(mox_service.MoxRuntimeNotReadyError, match="mox quickstart"):
        service.ensure_runtime_ready()


def test_runtime_ready_allows_compose_fallback(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    (settings.config_root.resolve().parent / "compose.yaml").write_text(
        "services: {}\n",
        encoding="utf-8",
    )

    def fake_which(command: str):
        if command == "docker":
            return "/usr/bin/docker"
        return None

    monkeypatch.setattr(mox_service.shutil, "which", fake_which)

    service = mox_service.MoxSyncService(settings)

    service.ensure_runtime_ready()


def test_compose_fallback_execs_into_api_container(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    calls = []
    (settings.config_root.resolve().parent / "compose.yaml").write_text(
        "services: {}\n",
        encoding="utf-8",
    )

    def fake_which(command: str):
        if command == "docker":
            return "/usr/bin/docker"
        return None

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mox_service.shutil, "which", fake_which)
    monkeypatch.setattr(mox_service.subprocess, "run", fake_run)

    service = mox_service.MoxSyncService(settings)
    service._run(["mox", "config", "domain", "add", "example.test", "admin", "admin"])

    assert calls[0][0][:6] == [
        "docker",
        "compose",
        "exec",
        "-T",
        "-e",
        "MOXCONF=/app/runtime/mox/config/mox.conf",
    ]
    assert calls[0][0][6:8] == ["api", "mox"]
    assert calls[0][1]["cwd"] == settings.config_root.resolve().parent


def test_quickstart_runtime_rewrites_container_unsafe_config(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        (settings.mox_config_dir / "mox.conf").write_text(
            "\n".join(
                [
                    "User: root",
                    "Listeners:",
                    "\tinternal:",
                    "\t\tAccountHTTP:",
                    "\t\t\tEnabled: true",
                    "\t\tAdminHTTP:",
                    "\t\t\tEnabled: true",
                    "\t\tWebmailHTTP:",
                    "\t\t\tEnabled: true",
                    "\t\tWebAPIHTTP:",
                    "\t\t\tEnabled: true",
                    "\tpublic:",
                    "\t\tIPs:",
                    "\t\t\t- 172.18.0.2",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(mox_service.subprocess, "run", fake_run)

    service = mox_service.MoxSyncService(settings)
    service.quickstart_runtime()

    text = (settings.mox_config_dir / "mox.conf").read_text(encoding="utf-8")
    assert "User: 1000" in text
    assert "\t\t\t- 0.0.0.0" in text
    assert "\t\t\t- ::" in text
    assert "\t\t\tEnabled: false" in text
    assert calls[0][0][:7] == [
        "docker",
        "compose",
        "run",
        "--rm",
        "mox",
        "mox",
        "quickstart",
    ]


def test_run_ignores_already_present_messages(monkeypatch, tmp_path):
    settings = _settings(tmp_path)
    monkeypatch.setattr(mox_service.shutil, "which", lambda command: "/usr/local/bin/mox")

    def fake_run(command, **kwargs):
        return SimpleNamespace(
            returncode=1,
            stdout="adding domain: bad request: domain already present",
            stderr="",
        )

    monkeypatch.setattr(mox_service.subprocess, "run", fake_run)

    service = mox_service.MoxSyncService(settings)
    result = service._run(
        ["mox", "config", "domain", "add", "example.test", "admin", "admin"],
        ignore_already_exists=True,
    )

    assert "already present" in result.stdout

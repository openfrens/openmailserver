from __future__ import annotations

from typer.testing import CliRunner

from openmailserver import cli
from openmailserver.cli import app

runner = CliRunner()


def test_install_command_writes_runtime():
    result = runner.invoke(app, ["install"])
    assert result.exit_code == 0
    assert "admin_api_key" in result.stdout
    assert "runtime_files" in result.stdout
    assert "container-mox" in result.stdout
    assert "quickstart_command" in result.stdout
    assert "docker compose up -d" in result.stdout


def test_plan_dns_command_outputs_records():
    result = runner.invoke(app, ["plan-dns"])
    assert result.exit_code == 0
    assert "MX" in result.stdout


def test_create_mailbox_delegates_to_api_container(monkeypatch):
    monkeypatch.setattr(
        cli,
        "get_settings",
        lambda: type("Settings", (), {"database_host": "postgres"})(),
    )
    monkeypatch.setattr(cli, "_compose_available", lambda: True)
    delegated = {}

    def fake_delegate(args: list[str]) -> None:
        delegated["args"] = args

    monkeypatch.setattr(cli, "_delegate_to_api_container", fake_delegate)

    result = runner.invoke(app, ["create-mailbox", "agent", "example.test", "--password", "secret"])

    assert result.exit_code == 0
    assert delegated["args"] == [
        "create-mailbox",
        "agent",
        "example.test",
        "--password",
        "secret",
    ]


def test_set_mailbox_password_delegates_to_api_container(monkeypatch):
    monkeypatch.setattr(
        cli,
        "get_settings",
        lambda: type("Settings", (), {"database_host": "postgres"})(),
    )
    monkeypatch.setattr(cli, "_compose_available", lambda: True)
    delegated = {}

    def fake_delegate(args: list[str]) -> None:
        delegated["args"] = args

    monkeypatch.setattr(cli, "_delegate_to_api_container", fake_delegate)

    result = runner.invoke(
        app, ["set-mailbox-password", "agent@example.test", "--password", "secret"]
    )

    assert result.exit_code == 0
    assert delegated["args"] == [
        "set-mailbox-password",
        "agent@example.test",
        "--password",
        "secret",
    ]

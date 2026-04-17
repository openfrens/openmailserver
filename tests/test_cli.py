from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from openmailserver import cli
from openmailserver.cli import _install_settings_with_overrides, app
from openmailserver.config import Settings

runner = CliRunner()


def test_install_command_writes_runtime(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cli.get_settings.cache_clear()

    result = runner.invoke(
        app,
        ["install", "--domain", "example.test", "--hostname", "mail.example.test"],
    )

    assert result.exit_code == 0
    assert "admin_api_key" in result.stdout
    assert "published_ports" in result.stdout
    assert "runtime_files" in result.stdout
    assert "container-mox" in result.stdout
    assert "quickstart_command" in result.stdout
    assert "docker compose up -d" in result.stdout
    env_contents = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "OPENMAILSERVER_PRIMARY_DOMAIN=example.test" in env_contents
    assert "OPENMAILSERVER_CANONICAL_HOSTNAME=mail.example.test" in env_contents


def test_install_command_writes_bind_overrides_in_env():
    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            [
                "install",
                "--domain",
                "example.test",
                "--hostname",
                "mail.example.test",
                "--api-bind",
                "127.0.0.1:9787",
                "--mox-http-bind",
                "127.0.0.1:8080",
                "--mox-https-bind",
                "127.0.0.1:8443",
            ],
        )

        assert result.exit_code == 0
        env_text = Path(".env").read_text(encoding="utf-8")
        assert "OPENMAILSERVER_API_BIND=127.0.0.1:9787" in env_text
        assert "OPENMAILSERVER_MOX_HTTP_BIND=127.0.0.1:8080" in env_text
        assert "OPENMAILSERVER_MOX_HTTPS_BIND=127.0.0.1:8443" in env_text


def test_bootstrap_command_runs_install_and_doctor():
    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            ["bootstrap", "--domain", "example.test", "--hostname", "mail.example.test"],
        )
        assert result.exit_code == 0
        assert "admin_api_key" in result.stdout
        assert "published_ports" in result.stdout
        assert "container-mox" in result.stdout
        env_text = Path(".env").read_text(encoding="utf-8")
        assert "OPENMAILSERVER_API_BIND=8787" in env_text
        assert "OPENMAILSERVER_MOX_HTTP_BIND=80" in env_text
        assert "OPENMAILSERVER_MOX_HTTPS_BIND=443" in env_text
        assert "OPENMAILSERVER_PRIMARY_DOMAIN=example.test" in env_text
        assert "OPENMAILSERVER_CANONICAL_HOSTNAME=mail.example.test" in env_text


def test_install_settings_with_overrides_no_overrides():
    settings = Settings()
    result = _install_settings_with_overrides(settings)
    assert result is settings


def test_install_settings_with_overrides_partial():
    settings = Settings()
    result = _install_settings_with_overrides(settings, api_bind="127.0.0.1:9787")
    assert result.api_bind == "127.0.0.1:9787"
    assert result.mox_http_bind == settings.mox_http_bind
    assert result.mox_https_bind == settings.mox_https_bind


def test_install_settings_with_overrides_all():
    settings = Settings()
    result = _install_settings_with_overrides(
        settings,
        api_bind="127.0.0.1:9787",
        mox_http_bind="127.0.0.1:8080",
        mox_https_bind="127.0.0.1:8443",
    )
    assert result.api_bind == "127.0.0.1:9787"
    assert result.mox_http_bind == "127.0.0.1:8080"
    assert result.mox_https_bind == "127.0.0.1:8443"


def test_plan_dns_command_outputs_records():
    cli.get_settings.cache_clear()
    result = runner.invoke(app, ["plan-dns", "--public-ip", "198.51.100.24"])
    assert result.exit_code == 0
    assert "MX" in result.stdout
    assert "198.51.100.24" in result.stdout


def test_plan_dns_command_requires_public_ip():
    cli.get_settings.cache_clear()
    result = runner.invoke(app, ["plan-dns"])

    assert result.exit_code == 2
    assert "Usage:" in result.output


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

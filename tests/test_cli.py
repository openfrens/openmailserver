from __future__ import annotations

from typer.testing import CliRunner

from openmailserver.cli import app

runner = CliRunner()


def test_install_command_writes_runtime(monkeypatch):
    captured = {}

    def fake_run_install(settings, adapter, repo_root, **kwargs):
        captured["kwargs"] = kwargs
        return {
            "status": "ok",
            "platform": "linux",
            "env_file": ".env",
            "service_file": "runtime/openmailserver.service",
            "install_hint": [],
            "service_hint": [],
            "runtime_files": {"install_script": "runtime/scripts/install-mail-stack-linux.sh"},
            "admin_api_key": "test-key",
            "installer": {
                "state_file": "runtime/install-state.json",
                "status": "completed",
                "current_phase": None,
                "phases": [],
                "next_action": None,
                "generate_only": False,
                "doctor": {"status": "warn"},
            },
        }

    monkeypatch.setattr("openmailserver.cli.run_install", fake_run_install)
    result = runner.invoke(app, ["install"])

    assert result.exit_code == 0
    assert "admin_api_key" in result.stdout
    assert "runtime_files" in result.stdout
    assert "install-mail-stack" in result.stdout
    assert '"status": "completed"' in result.stdout
    assert captured["kwargs"] == {
        "resume": False,
        "generate_only": False,
        "completed_phase": None,
    }


def test_install_command_supports_resume_flags(monkeypatch):
    captured = {}

    def fake_run_install(settings, adapter, repo_root, **kwargs):
        captured["kwargs"] = kwargs
        return {
            "status": "handoff",
            "platform": "linux",
            "env_file": ".env",
            "service_file": "runtime/openmailserver.service",
            "install_hint": [],
            "service_hint": [],
            "runtime_files": {},
            "admin_api_key": "test-key",
            "installer": {
                "state_file": "runtime/install-state.json",
                "status": "handoff",
                "current_phase": "mail_stack_install",
                "phases": [],
                "next_action": "resume",
                "generate_only": False,
                "doctor": None,
            },
        }

    monkeypatch.setattr("openmailserver.cli.run_install", fake_run_install)
    result = runner.invoke(
        app,
        ["install", "--resume", "--completed-phase", "mail_stack_install"],
    )

    assert result.exit_code == 0
    assert captured["kwargs"] == {
        "resume": True,
        "generate_only": False,
        "completed_phase": "mail_stack_install",
    }


def test_install_command_exits_nonzero_on_failure(monkeypatch):
    def fake_run_install(settings, adapter, repo_root, **kwargs):
        return {
            "status": "failed",
            "platform": "linux",
            "env_file": ".env",
            "service_file": "runtime/openmailserver.service",
            "install_hint": [],
            "service_hint": [],
            "runtime_files": {},
            "admin_api_key": "test-key",
            "installer": {
                "state_file": "runtime/install-state.json",
                "status": "failed",
                "current_phase": "apply_config",
                "phases": [],
                "next_action": "resume",
                "generate_only": False,
                "doctor": None,
            },
        }

    monkeypatch.setattr("openmailserver.cli.run_install", fake_run_install)
    result = runner.invoke(app, ["install"])

    assert result.exit_code == 1


def test_plan_dns_command_outputs_records():
    result = runner.invoke(app, ["plan-dns"])
    assert result.exit_code == 0
    assert "MX" in result.stdout


def test_domains_commands_manage_domain_lifecycle():
    attach = runner.invoke(
        app,
        [
            "domains",
            "attach",
            "external.test",
            "--dns-mode",
            "external",
        ],
    )
    verify = runner.invoke(
        app,
        [
            "domains",
            "verify",
            "external.test",
            "--confirm-records",
        ],
    )
    status = runner.invoke(app, ["domains", "status", "external.test"])

    assert attach.exit_code == 0
    assert verify.exit_code == 0
    assert '"verification_status": "verified"' in status.stdout

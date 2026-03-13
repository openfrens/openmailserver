from __future__ import annotations

from typer.testing import CliRunner

from openmailserver.cli import app

runner = CliRunner()


def test_install_command_writes_runtime():
    result = runner.invoke(app, ["install"])
    assert result.exit_code == 0
    assert "admin_api_key" in result.stdout
    assert "runtime_files" in result.stdout
    assert "install-mail-stack" in result.stdout


def test_plan_dns_command_outputs_records():
    result = runner.invoke(app, ["plan-dns"])
    assert result.exit_code == 0
    assert "MX" in result.stdout

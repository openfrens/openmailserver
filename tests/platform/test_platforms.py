from __future__ import annotations

from openmailserver.platform.linux import LinuxAdapter
from openmailserver.platform.macos import MacOSAdapter


def test_linux_adapter_produces_service_unit(tmp_path):
    adapter = LinuxAdapter()
    unit = adapter.api_service_unit(tmp_path)
    assert "ExecStart" in unit
    assert "uvicorn" in unit
    assert str(tmp_path / ".venv" / "bin" / "python") in unit
    install_script = adapter.install_script({"repo_root": str(tmp_path)})
    apply_script = adapter.apply_config_script({"repo_root": str(tmp_path)})
    service_install_script = adapter.install_api_service_script({"repo_root": str(tmp_path)})
    assert "postfix" in install_script
    assert "python3-venv" in install_script
    assert "dovecot-lmtpd" in install_script
    assert "postfix-pgsql" in install_script
    assert "dovecot-pgsql" in install_script
    assert "python3.11" not in install_script
    assert "/etc/postfix/main.cf" in apply_script
    assert "install-mail-stack-linux.sh successfully" in apply_script
    assert "openmailserver.service" in service_install_script


def test_macos_adapter_produces_service_unit(tmp_path):
    adapter = MacOSAdapter()
    unit = adapter.api_service_unit(tmp_path)
    assert "plist" in unit
    assert "uvicorn" in unit
    assert str(tmp_path / ".venv" / "bin" / "python") in unit
    install_script = adapter.install_script({"repo_root": str(tmp_path)})
    apply_script = adapter.apply_config_script({"repo_root": str(tmp_path)})
    service_install_script = adapter.install_api_service_script({"repo_root": str(tmp_path)})
    assert "brew install" in install_script
    assert "/etc/postfix/main.cf" in apply_script
    assert "ai.openmailserver.api.plist" in service_install_script

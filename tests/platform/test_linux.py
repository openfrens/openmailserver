from __future__ import annotations

from openmailserver.platform.linux import LinuxAdapter


def test_linux_adapter_hints_and_checks(tmp_path):
    adapter = LinuxAdapter()

    assert any("apt-get" in hint for hint in adapter.install_hint())
    assert any("systemctl" in hint for hint in adapter.service_hint())
    assert [check.status for check in adapter.platform_checks(tmp_path)] == ["pass", "pass", "pass"]


def test_linux_adapter_renders_service_unit_and_scripts(tmp_path):
    adapter = LinuxAdapter()
    unit = adapter.api_service_unit(tmp_path)
    install_script = adapter.install_script({"repo_root": str(tmp_path)})
    apply_script = adapter.apply_config_script({"repo_root": str(tmp_path)})
    service_install_script = adapter.install_api_service_script({"repo_root": str(tmp_path)})
    service_status_script = adapter.status_api_service_script({"repo_root": str(tmp_path)})

    assert "Description=Openmailserver API" in unit
    assert str(tmp_path / ".venv" / "bin" / "python") in unit
    assert "uvicorn openmailserver.app:app" in unit
    assert "apt-get install" in install_script
    assert "curl" in install_script
    assert "postfix-pgsql" in install_script
    assert "dovecot-pgsql" in install_script
    assert "cp \"$RUNTIME_ROOT/postfix/main.cf\"" in apply_script
    assert "enable --now openmailserver.service" in service_install_script
    assert "systemctl status openmailserver.service" in service_status_script

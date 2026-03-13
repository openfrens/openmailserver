from __future__ import annotations

from openmailserver.platform.macos import MacOSAdapter


def test_macos_adapter_hints_and_checks(tmp_path):
    adapter = MacOSAdapter()

    assert any("brew install" in hint for hint in adapter.install_hint())
    assert any("launchctl" in hint for hint in adapter.service_hint())
    assert [check.status for check in adapter.platform_checks(tmp_path)] == ["pass", "pass", "warn"]


def test_macos_adapter_renders_service_unit_and_scripts(tmp_path):
    adapter = MacOSAdapter()
    unit = adapter.api_service_unit(tmp_path)
    install_script = adapter.install_script({"repo_root": str(tmp_path)})
    apply_script = adapter.apply_config_script({"repo_root": str(tmp_path)})

    assert "<plist version=\"1.0\">" in unit
    assert "<string>uvicorn</string>" in unit
    assert "brew services start postgresql@16" in install_script
    assert "brew services restart dovecot" in apply_script

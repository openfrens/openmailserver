from __future__ import annotations

import pytest

from openmailserver.platform.detect import current_platform
from openmailserver.platform.linux import LinuxAdapter
from openmailserver.platform.macos import MacOSAdapter


def test_current_platform_returns_macos_adapter(monkeypatch):
    monkeypatch.setattr("openmailserver.platform.detect.platform.system", lambda: "Darwin")

    assert isinstance(current_platform(), MacOSAdapter)


def test_current_platform_returns_linux_adapter(monkeypatch):
    monkeypatch.setattr("openmailserver.platform.detect.platform.system", lambda: "Linux")

    assert isinstance(current_platform(), LinuxAdapter)


def test_current_platform_rejects_unknown_system(monkeypatch):
    monkeypatch.setattr("openmailserver.platform.detect.platform.system", lambda: "Plan9")

    with pytest.raises(RuntimeError, match="Unsupported platform"):
        current_platform()

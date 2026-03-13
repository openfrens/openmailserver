from __future__ import annotations

import platform

from openmailserver.platform.base import PlatformAdapter
from openmailserver.platform.linux import LinuxAdapter
from openmailserver.platform.macos import MacOSAdapter


def current_platform() -> PlatformAdapter:
    system = platform.system().lower()
    if system == "darwin":
        return MacOSAdapter()
    if system == "linux":
        return LinuxAdapter()
    raise RuntimeError(f"Unsupported platform: {system}")

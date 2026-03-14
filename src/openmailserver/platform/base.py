from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class PlatformCheck:
    name: str
    status: str
    details: str


class PlatformAdapter:
    name = "unknown"

    def install_hint(self) -> list[str]:
        return []

    def service_hint(self) -> list[str]:
        return []

    def platform_checks(self, root: Path) -> list[PlatformCheck]:
        return []

    def api_service_unit(self, root: Path) -> str:
        raise NotImplementedError

    def install_script(self, context: dict[str, str]) -> str:
        raise NotImplementedError

    def apply_config_script(self, context: dict[str, str]) -> str:
        raise NotImplementedError

    def install_api_service_script(self, context: dict[str, str]) -> str:
        raise NotImplementedError

    def start_api_service_script(self, context: dict[str, str]) -> str:
        raise NotImplementedError

    def stop_api_service_script(self, context: dict[str, str]) -> str:
        raise NotImplementedError

    def restart_api_service_script(self, context: dict[str, str]) -> str:
        raise NotImplementedError

    def status_api_service_script(self, context: dict[str, str]) -> str:
        raise NotImplementedError

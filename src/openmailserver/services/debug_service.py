from __future__ import annotations

import platform
import shutil
import socket
import subprocess
from pathlib import Path

from sqlalchemy.orm import Session

from openmailserver.config import get_settings
from openmailserver.services.dns_service import build_dns_plan
from openmailserver.services.logging_service import tail_log_file
from openmailserver.services.mox_service import MoxSyncService
from openmailserver.services.queue_service import list_queue


def _check(name: str, status: str, details: str) -> dict[str, str]:
    return {"name": name, "status": status, "details": details}


def _binary_check(name: str, command: str, missing_details: str) -> dict[str, str]:
    available = shutil.which(command) is not None
    return _check(
        name,
        "pass" if available else "warn",
        f"{command} is available." if available else missing_details,
    )


def _docker_compose_check() -> dict[str, str]:
    try:
        subprocess.run(
            ["docker", "compose", "version"],
            check=True,
            capture_output=True,
            text=True,
        )
        return _check("docker_compose", "pass", "docker compose is available.")
    except (FileNotFoundError, subprocess.CalledProcessError):
        return _check(
            "docker_compose",
            "warn",
            "docker compose is missing. Install Docker Compose v2 before starting the stack.",
        )


def _path_check(name: str, path: Path, missing_details: str) -> dict[str, str]:
    exists = path.exists()
    return _check(
        name,
        "pass" if exists else "warn",
        f"{path} exists." if exists else missing_details,
    )


def health_report() -> dict:
    settings = get_settings()
    runtime_platform = platform.system().lower()
    checks = {
        "platform": runtime_platform,
        "runtime": "mox",
        "hostname": socket.gethostname(),
        "canonical_hostname": settings.canonical_hostname,
        "smtp_host": settings.smtp_host,
        "debug_api_enabled": str(settings.debug_api_enabled).lower(),
    }
    return {"status": "ok", "platform": runtime_platform, "checks": checks}


def doctor_report(root: Path | None = None) -> dict:
    settings = get_settings()
    mox_service = MoxSyncService(settings)
    root = root or settings.config_root
    checks = []
    checks.append(
        _binary_check(
            "docker_binary",
            "docker",
            "docker is missing. Install Docker Engine before running the containerized stack.",
        )
    )
    checks.append(
        _check(
            "mox_binary",
            "pass" if mox_service.has_runtime_executor() else "warn",
            (
                "mox commands are available through the current runtime."
                if mox_service.has_runtime_executor()
                else (
                    "mox is missing from the API runtime and Docker Compose is not "
                    "available. Rebuild the API image or install the CLI first."
                )
            ),
        )
    )
    checks.append(_docker_compose_check())
    checks.append(
        _path_check(
            "compose_file",
            Path.cwd() / "compose.yaml",
            "compose.yaml is missing. Restore the checked-in container stack definition.",
        )
    )
    checks.append(
        _path_check(
            "mox_runtime_dir",
            root / "mox",
            (
                "runtime/mox is missing. Run openmailserver install to prepare the "
                "runtime directories."
            ),
        )
    )
    checks.append(
        _path_check(
            "mox_config_dir",
            settings.mox_config_dir,
            "runtime/mox/config is missing. Run openmailserver install and mox quickstart first.",
        )
    )
    mox_conf = settings.mox_config_dir / "mox.conf"
    mox_initialized = mox_conf.exists()
    checks.append(
        _check(
            "mox_quickstart",
            "pass" if mox_initialized else "warn",
            (
                "mox.conf is present."
                if mox_initialized
                else (
                    "mox quickstart has not been completed yet. "
                    "Run openmailserver mox-quickstart."
                )
            ),
        )
    )
    has_admin_key = bool(settings.admin_api_key)
    checks.append(
        _check(
            "secrets",
            "pass" if has_admin_key else "warn",
            (
                "Admin API key configured."
                if has_admin_key
                else "Admin API key missing. Run install to generate one."
            ),
        )
    )
    checks.append(
        _check("port25", "warn", "Direct-to-MX requires outbound port 25 reachability.")
    )
    return {
        "status": "ok" if all(check["status"] == "pass" for check in checks) else "warn",
        "platform": platform.system().lower(),
        "checks": checks,
        "dns_plan": build_dns_plan(),
    }


def config_report() -> dict:
    settings = get_settings()
    return {
        "env": settings.env,
        "host": settings.host,
        "port": settings.port,
        "maildir_root": str(settings.maildir_root),
        "attachment_root": str(settings.attachment_root),
        "canonical_hostname": settings.canonical_hostname,
        "primary_domain": settings.primary_domain,
        "public_ip": settings.public_ip,
        "mox_image": settings.mox_image,
        "mox_admin_account": settings.mox_admin_account,
        "mox_admin_address": settings.effective_mox_admin_address,
        "database_url": "***redacted***",
        "admin_api_key": "***configured***" if settings.admin_api_key else "***missing***",
        "backup_encryption_key": (
            "***configured***" if settings.backup_encryption_key else "***missing***"
        ),
    }


def debug_bundle(db: Session) -> dict:
    return {
        "health": health_report(),
        "doctor": doctor_report(),
        "queue": [entry.model_dump() for entry in list_queue(db)],
        "logs": tail_log_file(50),
    }

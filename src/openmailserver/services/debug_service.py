from __future__ import annotations

import platform
import socket
from pathlib import Path

from sqlalchemy.orm import Session

from openmailserver.config import get_settings
from openmailserver.platform.base import PlatformCheck
from openmailserver.platform.detect import current_platform
from openmailserver.services.dns_service import build_dns_plan
from openmailserver.services.logging_service import tail_log_file
from openmailserver.services.queue_service import list_queue


def health_report() -> dict:
    settings = get_settings()
    adapter = current_platform()
    checks = {
        "platform": adapter.name,
        "hostname": socket.gethostname(),
        "canonical_hostname": settings.canonical_hostname,
        "debug_api_enabled": str(settings.debug_api_enabled).lower(),
    }
    return {"status": "ok", "platform": adapter.name, "checks": checks}


def doctor_report(root: Path | None = None) -> dict:
    settings = get_settings()
    adapter = current_platform()
    root = root or settings.data_dir
    checks = []
    checks.extend(adapter.platform_checks(root))
    checks.append(
        PlatformCheck(
            "secrets",
            "pass" if settings.admin_api_key else "warn",
            (
                "Admin API key configured."
                if settings.admin_api_key
                else "Admin API key missing. Run install to generate one."
            ),
        )
    )
    checks.append(
        PlatformCheck("port25", "warn", "Direct-to-MX requires outbound port 25 reachability.")
    )
    return {
        "status": "ok" if all(check.status == "pass" for check in checks) else "warn",
        "platform": platform.system().lower(),
        "checks": [
            {"name": check.name, "status": check.status, "details": check.details}
            for check in checks
        ],
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

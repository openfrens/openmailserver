from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from openmailserver.config import get_settings
from openmailserver.models import SystemLog
from openmailserver.security import redact_text


def write_system_log(
    db: Session, level: str, event_type: str, message: str, metadata: dict | None = None
) -> None:
    entry = SystemLog(
        level=level,
        event_type=event_type,
        message=redact_text(message),
        payload=metadata or {},
    )
    db.add(entry)

    settings = get_settings()
    settings.log_file.parent.mkdir(parents=True, exist_ok=True)
    with settings.log_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(
            {
                "level": level,
                "event_type": event_type,
                "message": redact_text(message),
                "metadata": metadata or {},
            }
        ))
        handle.write("\n")


def tail_log_file(limit: int = 100) -> list[str]:
    path: Path = get_settings().log_file
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return lines[-limit:]

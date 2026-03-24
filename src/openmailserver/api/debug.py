from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from openmailserver.deps import get_db, require_api_key, require_debug_api_enabled
from openmailserver.schemas import (
    BackupResponse,
    DebugReport,
    DnsPlanResponse,
    QueueEntry,
)
from openmailserver.security import ADMIN_SCOPE, DEBUG_READ_SCOPE
from openmailserver.services.backup_service import create_backup, validate_backup
from openmailserver.services.debug_service import (
    config_report,
    debug_bundle,
    doctor_report,
)
from openmailserver.services.dns_service import build_dns_plan
from openmailserver.services.logging_service import tail_log_file
from openmailserver.services.queue_service import (
    list_queue,
)
from openmailserver.services.queue_service import (
    message_trace as queue_message_trace,
)

router = APIRouter(dependencies=[Depends(require_debug_api_enabled)])


@router.get("/debug/health", response_model=DebugReport)
def debug_health(
    _: object = Depends(require_api_key(DEBUG_READ_SCOPE)),
) -> DebugReport:
    report = doctor_report()
    return DebugReport(status=report["status"], details=report)


@router.get("/debug/config", response_model=DebugReport)
def debug_config(
    _: object = Depends(require_api_key(DEBUG_READ_SCOPE)),
) -> DebugReport:
    report = config_report()
    return DebugReport(status="ok", details=report)


@router.get("/debug/logs", response_model=DebugReport)
def debug_logs(
    _: object = Depends(require_api_key(DEBUG_READ_SCOPE)),
) -> DebugReport:
    return DebugReport(status="ok", details={"lines": tail_log_file(100)})


@router.get("/queue", response_model=list[QueueEntry])
def queue(
    db: Session = Depends(get_db),
    _: object = Depends(require_api_key(DEBUG_READ_SCOPE)),
) -> list[QueueEntry]:
    return list_queue(db)


@router.get("/debug/queue/{queue_id}", response_model=DebugReport)
def debug_queue(
    queue_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(require_api_key(DEBUG_READ_SCOPE)),
) -> DebugReport:
    entries = list_queue(db)
    items = [entry for entry in entries if entry.queue_id == queue_id or str(entry.id) == queue_id]
    return DebugReport(
        status="ok" if items else "missing",
        details={"items": [entry.model_dump(by_alias=True) for entry in items]},
    )


@router.get("/debug/messages/{message_id}/trace", response_model=DebugReport)
def message_trace(
    message_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_api_key(DEBUG_READ_SCOPE)),
) -> DebugReport:
    trace = queue_message_trace(db, message_id)
    return DebugReport(status=trace["status"], details=trace)


@router.get("/debug/deliverability/report", response_model=DebugReport)
@router.get("/deliverability/report", response_model=DebugReport)
def deliverability_report(
    _: object = Depends(require_api_key(DEBUG_READ_SCOPE)),
) -> DebugReport:
    report = doctor_report()
    return DebugReport(status=report["status"], details=report)


@router.post("/backup", response_model=BackupResponse)
def backup(
    db: Session = Depends(get_db),
    _: object = Depends(require_api_key(ADMIN_SCOPE)),
) -> BackupResponse:
    path = create_backup(db)
    return BackupResponse(path=str(path), encrypted=True)


@router.post("/restore/validate", response_model=DebugReport)
def validate_backup_archive(
    path: str,
    _: object = Depends(require_api_key(ADMIN_SCOPE)),
) -> DebugReport:
    report = validate_backup(Path(path))
    return DebugReport(status=report["status"], details=report)


@router.get("/plan-dns", response_model=DnsPlanResponse)
def plan_dns(
    _: object = Depends(require_api_key(DEBUG_READ_SCOPE)),
) -> DnsPlanResponse:
    records = build_dns_plan()
    hostname = records[0]["host"]
    domain = next((record["host"] for record in records if record["type"] == "MX"), hostname)
    return DnsPlanResponse(hostname=hostname, domain=domain, records=records)


@router.get("/debug/bundle", response_model=DebugReport)
def bundle(
    db: Session = Depends(get_db),
    _: object = Depends(require_api_key(DEBUG_READ_SCOPE)),
) -> DebugReport:
    report = debug_bundle(db)
    doctor_ok = report["doctor"]["status"] == "ok"
    health_ok = report["health"]["status"] == "ok"
    status = "ok" if doctor_ok and health_ok else "warn"
    return DebugReport(status=status, details=report)

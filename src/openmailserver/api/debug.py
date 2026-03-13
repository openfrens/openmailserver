from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from openmailserver.deps import get_db, require_api_key
from openmailserver.schemas import BackupResponse, DebugReport, DnsPlanResponse
from openmailserver.services.backup_service import create_backup, validate_backup
from openmailserver.services.debug_service import (
    config_report,
    debug_bundle,
    debug_trace,
    doctor_report,
)
from openmailserver.services.dns_service import build_dns_plan
from openmailserver.services.logging_service import tail_log_file
from openmailserver.services.queue_service import list_queue

router = APIRouter()


@router.get("/debug/health", response_model=DebugReport)
def debug_health(
    _: object = Depends(require_api_key("debug:read")),
) -> DebugReport:
    report = doctor_report()
    return DebugReport(status=report["status"], details=report)


@router.get("/debug/config", response_model=DebugReport)
def debug_config(
    _: object = Depends(require_api_key("debug:read")),
) -> DebugReport:
    report = config_report()
    return DebugReport(status="ok", details=report)


@router.get("/debug/logs", response_model=DebugReport)
def debug_logs(
    _: object = Depends(require_api_key("debug:read")),
) -> DebugReport:
    return DebugReport(status="ok", details={"lines": tail_log_file(100)})


@router.get("/queue", response_model=list[dict])
def queue(
    db: Session = Depends(get_db),
    _: object = Depends(require_api_key("debug:read")),
) -> list[dict]:
    return list_queue(db)


@router.get("/debug/queue/{queue_id}", response_model=DebugReport)
def debug_queue(
    queue_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(require_api_key("debug:read")),
) -> DebugReport:
    items = [
        item
        for item in list_queue(db)
        if item["queue_id"] == queue_id or str(item["id"]) == queue_id
    ]
    return DebugReport(status="ok" if items else "missing", details={"items": items})


@router.get("/debug/messages/{message_id}/trace", response_model=DebugReport)
def message_trace(
    message_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_api_key("debug:read")),
) -> DebugReport:
    trace = debug_trace(db, message_id)
    return DebugReport(status=trace["status"], details=trace)


@router.get("/debug/deliverability/report", response_model=DebugReport)
@router.get("/deliverability/report", response_model=DebugReport)
def deliverability_report(
    _: object = Depends(require_api_key("debug:read")),
) -> DebugReport:
    report = doctor_report()
    return DebugReport(status=report["status"], details=report)


@router.post("/backup", response_model=BackupResponse)
def backup(
    db: Session = Depends(get_db),
    _: object = Depends(require_api_key("admin")),
) -> BackupResponse:
    path = create_backup(db)
    return BackupResponse(path=str(path), encrypted=True)


@router.post("/restore/validate", response_model=DebugReport)
def validate_restore(
    path: str,
    _: object = Depends(require_api_key("admin")),
) -> DebugReport:
    report = validate_backup(Path(path))
    return DebugReport(status=report["status"], details=report)


@router.get("/plan-dns", response_model=DnsPlanResponse)
def plan_dns(
    _: object = Depends(require_api_key("debug:read")),
) -> DnsPlanResponse:
    records = build_dns_plan()
    first = records[0]
    return DnsPlanResponse(hostname=first["host"], domain=first["host"], records=records)


@router.get("/debug/bundle", response_model=DebugReport)
def bundle(
    db: Session = Depends(get_db),
    _: object = Depends(require_api_key("debug:read")),
) -> DebugReport:
    return DebugReport(status="ok", details=debug_bundle(db))

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from openmailserver.api import debug
from openmailserver.schemas import QueueEntry


def test_debug_reports_wrap_service_results(monkeypatch):
    monkeypatch.setattr(
        debug,
        "doctor_report",
        lambda: {"status": "warn", "checks": [{"name": "port25", "status": "warn"}]},
    )
    monkeypatch.setattr(debug, "config_report", lambda: {"admin_api_key": "***configured***"})
    monkeypatch.setattr(debug, "tail_log_file", lambda limit: ["first", "second"][: limit or 2])

    health_report = debug.debug_health(_=object())
    config_report = debug.debug_config(_=object())
    logs_report = debug.debug_logs(_=object())
    deliverability = debug.deliverability_report(_=object())

    assert health_report.status == "warn"
    assert config_report.details["admin_api_key"] == "***configured***"
    assert logs_report.details["lines"] == ["first", "second"]
    assert deliverability.status == "warn"


def test_queue_and_trace_debug_endpoints(db_session, monkeypatch):
    monkeypatch.setattr(
        debug,
        "list_queue",
        lambda db: [
            QueueEntry(
                id=7,
                queue_id="q-7",
                state="queued",
                message_id=None,
                error=None,
                created_at=datetime(2026, 3, 13, tzinfo=UTC),
            ),
            QueueEntry(
                id=8,
                queue_id="q-8",
                state="sent",
                message_id=None,
                error=None,
                created_at=datetime(2026, 3, 14, tzinfo=UTC),
            ),
        ],
    )
    monkeypatch.setattr(
        debug,
        "queue_message_trace",
        lambda db, message_id: {"status": "sent", "events": [{"event_type": "sent"}]},
    )
    monkeypatch.setattr(
        debug,
        "debug_bundle",
        lambda db: {
            "health": {"status": "ok"},
            "doctor": {"status": "warn"},
            "queue": [{"id": 7}],
            "logs": ["x"],
        },
    )

    queue_items = debug.queue(db=db_session, _=object())
    queue_report = debug.debug_queue("q-7", db=db_session, _=object())
    trace_report = debug.message_trace(7, db=db_session, _=object())
    bundle_report = debug.bundle(db=db_session, _=object())

    assert len(queue_items) == 2
    assert queue_items[0].id == 7
    assert queue_report.status == "ok"
    assert queue_report.details["items"][0]["id"] == 7
    assert trace_report.status == "sent"
    assert bundle_report.status == "warn"
    assert bundle_report.details["queue"][0]["id"] == 7


def test_backup_validate_and_dns_debug_endpoints(db_session, monkeypatch):
    monkeypatch.setattr(debug, "create_backup", lambda db: Path("/tmp/openmailserver.tar.gz.enc"))
    monkeypatch.setattr(debug, "validate_backup", lambda path: {"status": "ok", "entries": ["a"]})
    monkeypatch.setattr(
        debug,
        "build_dns_plan",
        lambda: [
            {"type": "A", "host": "mail.example.test", "value": "127.0.0.1"},
            {"type": "MX", "host": "example.test", "value": "10 mail.example.test."},
        ],
    )

    backup_report = debug.backup(db=db_session, _=object())
    validate_report = debug.validate_backup_archive("/tmp/openmailserver.tar.gz.enc", _=object())
    dns_report = debug.plan_dns(_=object())

    assert backup_report.encrypted is True
    assert validate_report.status == "ok"
    assert dns_report.hostname == "mail.example.test"
    assert dns_report.domain == "example.test"
    assert dns_report.records[1]["type"] == "MX"

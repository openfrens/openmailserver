from __future__ import annotations

from types import SimpleNamespace

from openmailserver.models import SystemLog
from openmailserver.services import logging_service


def test_write_system_log_persists_redacted_entry_and_file(db_session, monkeypatch, tmp_path):
    log_file = tmp_path / "logs" / "openmailserver.log"
    monkeypatch.setattr(logging_service, "get_settings", lambda: SimpleNamespace(log_file=log_file))

    logging_service.write_system_log(
        db_session,
        "error",
        "auth_failure",
        "api_key=super-secret",
        {"source": "test"},
    )
    db_session.commit()

    stored = db_session.query(SystemLog).one()
    lines = logging_service.tail_log_file()

    assert stored.event_type == "auth_failure"
    assert "***REDACTED***" in stored.message
    assert len(lines) == 1
    assert "***REDACTED***" in lines[0]


def test_tail_log_file_returns_last_lines(monkeypatch, tmp_path):
    log_file = tmp_path / "openmailserver.log"
    log_file.write_text("one\ntwo\nthree\n", encoding="utf-8")
    monkeypatch.setattr(logging_service, "get_settings", lambda: SimpleNamespace(log_file=log_file))

    assert logging_service.tail_log_file(limit=2) == ["two", "three"]

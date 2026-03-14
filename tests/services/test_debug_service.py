from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from openmailserver.platform.base import PlatformCheck
from openmailserver.schemas import QueueEntry
from openmailserver.services import debug_service


class _Adapter:
    name = "linux"

    def platform_checks(self, root: Path):
        return [
            PlatformCheck("runtime", "pass", "ready"),
            PlatformCheck("mail_stack", "warn", "verify packages"),
        ]


def test_health_report_uses_platform_and_settings(monkeypatch):
    settings = SimpleNamespace(canonical_hostname="mail.example.test", debug_api_enabled=True)
    monkeypatch.setattr(debug_service, "get_settings", lambda: settings)
    monkeypatch.setattr(debug_service, "current_platform", lambda: _Adapter())
    monkeypatch.setattr(debug_service.socket, "gethostname", lambda: "snowbook.local")

    report = debug_service.health_report()

    assert report["status"] == "ok"
    assert report["platform"] == "linux"
    assert report["checks"]["hostname"] == "snowbook.local"


def test_doctor_and_config_reports_include_checks(monkeypatch, tmp_path):
    settings = SimpleNamespace(
        data_dir=tmp_path,
        admin_api_key=None,
        env="test",
        host="127.0.0.1",
        port=8787,
        maildir_root=tmp_path / "maildir",
        attachment_root=tmp_path / "attachments",
        canonical_hostname="mail.example.test",
        primary_domain="example.test",
        public_ip="127.0.0.1",
        database_url="sqlite:///hidden.sqlite3",
        backup_encryption_key="configured",
    )
    monkeypatch.setattr(debug_service, "get_settings", lambda: settings)
    monkeypatch.setattr(debug_service, "current_platform", lambda: _Adapter())
    monkeypatch.setattr(debug_service.platform, "system", lambda: "Linux")
    monkeypatch.setattr(debug_service, "build_dns_plan", lambda: [{"type": "MX"}])
    monkeypatch.setattr(debug_service.shutil, "which", lambda command: f"/usr/bin/{command}")

    doctor = debug_service.doctor_report()
    config = debug_service.config_report()

    assert doctor["status"] == "warn"
    assert any(check["name"] == "postfix_binary" for check in doctor["checks"])
    assert any(check["name"] == "dovecot_binary" for check in doctor["checks"])
    assert any(check["name"] == "postgres_binary" for check in doctor["checks"])
    assert any(check["name"] == "port25" for check in doctor["checks"])
    assert doctor["dns_plan"] == [{"type": "MX"}]
    assert config["database_url"] == "***redacted***"
    assert config["admin_api_key"] == "***missing***"
    assert config["backup_encryption_key"] == "***configured***"


def test_doctor_report_warns_when_required_binaries_are_missing(monkeypatch, tmp_path):
    settings = SimpleNamespace(
        data_dir=tmp_path,
        admin_api_key="configured",
        env="test",
        host="127.0.0.1",
        port=8787,
        maildir_root=tmp_path / "maildir",
        attachment_root=tmp_path / "attachments",
        canonical_hostname="mail.example.test",
        primary_domain="example.test",
        public_ip="127.0.0.1",
        database_url="sqlite:///hidden.sqlite3",
        backup_encryption_key="configured",
    )
    monkeypatch.setattr(debug_service, "get_settings", lambda: settings)
    monkeypatch.setattr(debug_service, "current_platform", lambda: _Adapter())
    monkeypatch.setattr(debug_service.platform, "system", lambda: "Linux")
    monkeypatch.setattr(debug_service, "build_dns_plan", lambda: [{"type": "MX"}])
    monkeypatch.setattr(debug_service.shutil, "which", lambda command: None)

    doctor = debug_service.doctor_report()
    checks = {check["name"]: check for check in doctor["checks"]}

    assert checks["postfix_binary"]["status"] == "warn"
    assert checks["dovecot_binary"]["status"] == "warn"
    assert checks["postgres_binary"]["status"] == "warn"


def test_debug_bundle_delegates_to_underlying_services(monkeypatch):
    monkeypatch.setattr(debug_service, "health_report", lambda: {"status": "ok"})
    monkeypatch.setattr(debug_service, "doctor_report", lambda: {"status": "warn"})
    monkeypatch.setattr(
        debug_service,
        "list_queue",
        lambda db: [
            QueueEntry(
                id=7,
                state="queued",
                queue_id=None,
                message_id=None,
                error=None,
                created_at=datetime(2026, 3, 13, tzinfo=UTC),
            )
        ],
    )
    monkeypatch.setattr(debug_service, "tail_log_file", lambda limit: ["first"])

    bundle = debug_service.debug_bundle(db=object())

    assert bundle["queue"][0]["id"] == 7
    assert bundle["logs"] == ["first"]

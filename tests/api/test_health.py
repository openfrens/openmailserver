from __future__ import annotations

from openmailserver.api import health


def test_health_endpoint_wraps_service_report(monkeypatch):
    monkeypatch.setattr(
        health,
        "health_report",
        lambda: {"status": "ok", "platform": "macos", "checks": {"debug_api_enabled": "true"}},
    )

    response = health.health()

    assert response.status == "ok"
    assert response.platform == "macos"
    assert response.checks["debug_api_enabled"] == "true"

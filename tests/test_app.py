from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from openmailserver import app as app_module
from openmailserver.database import SessionLocal
from openmailserver.models import ApiKey
from openmailserver.security import verify_api_key


def test_build_app_sets_settings_and_routes(monkeypatch):
    settings = object()
    calls = {"create_all": 0, "ensure_admin": 0}

    def fake_create_all(_settings=None) -> None:
        calls["create_all"] += 1

    def fake_ensure_admin_key() -> None:
        calls["ensure_admin"] += 1

    monkeypatch.setattr(app_module, "get_settings", lambda: settings)
    monkeypatch.setattr(app_module, "create_all", fake_create_all)
    monkeypatch.setattr(app_module, "_ensure_configured_admin_key", fake_ensure_admin_key)

    application = app_module.build_app()
    with TestClient(application):
        assert application.state.settings is settings

    assert isinstance(application, FastAPI)
    assert calls["create_all"] == 1
    assert calls["ensure_admin"] == 1
    assert any(route.path == "/health" for route in application.routes)


def test_ensure_configured_admin_key_persists_env_key(monkeypatch):
    monkeypatch.setattr(
        app_module,
        "get_settings",
        lambda: type("Settings", (), {"admin_api_key": "configured-admin-key"})(),
    )

    app_module._ensure_configured_admin_key()

    session = SessionLocal()
    try:
        keys = session.query(ApiKey).filter(ApiKey.revoked_at.is_(None)).all()
        assert any(verify_api_key("configured-admin-key", key.key_hash) for key in keys)
    finally:
        session.close()

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from openmailserver import app as app_module


def test_build_app_sets_settings_and_routes(monkeypatch):
    settings = object()
    calls = {"create_all": 0}

    def fake_create_all(_settings=None) -> None:
        calls["create_all"] += 1

    monkeypatch.setattr(app_module, "get_settings", lambda: settings)
    monkeypatch.setattr(app_module, "create_all", fake_create_all)

    application = app_module.build_app()
    with TestClient(application):
        assert application.state.settings is settings

    assert isinstance(application, FastAPI)
    assert calls["create_all"] == 1
    assert any(route.path == "/health" for route in application.routes)

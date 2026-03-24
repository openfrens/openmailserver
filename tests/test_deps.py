from __future__ import annotations

from contextlib import suppress
from types import SimpleNamespace

from fastapi import HTTPException, status
from starlette.requests import Request

from openmailserver import deps
from openmailserver.models import ApiKey
from openmailserver.security import hash_api_key


class _FakeSession:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _request_with_key(value: str | None) -> Request:
    headers = []
    if value is not None:
        headers.append((b"x-openmailserver-key", value.encode("utf-8")))
    return Request({"type": "http", "headers": headers})


def test_get_db_closes_session(monkeypatch):
    session = _FakeSession()
    monkeypatch.setattr(deps, "SessionLocal", lambda: session)

    generator = deps.get_db()

    assert next(generator) is session
    with suppress(StopIteration):
        next(generator)

    assert session.closed is True


def test_require_api_key_accepts_matching_scope(db_session):
    dependency = deps.require_api_key("debug:read")

    record = dependency(db=db_session, request=_request_with_key("test-admin-key"))

    assert record.name == "test-admin"
    assert "admin" in record.scopes


def test_require_api_key_rejects_missing_key(db_session):
    dependency = deps.require_api_key("debug:read")

    try:
        dependency(db=db_session, request=_request_with_key(None))
    except HTTPException as exc:
        assert exc.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc.detail == "Missing API key"
    else:
        raise AssertionError("missing API key should raise HTTPException")


def test_require_api_key_rejects_invalid_scope(db_session):
    db_session.add(
        ApiKey(
            name="limited",
            key_hash=hash_api_key("limited-key"),
            scopes=["mail:read"],
        )
    )
    db_session.commit()

    dependency = deps.require_api_key("mail:write")

    try:
        dependency(db=db_session, request=_request_with_key("limited-key"))
    except HTTPException as exc:
        assert exc.status_code == status.HTTP_403_FORBIDDEN
        assert exc.detail == "Invalid API key"
    else:
        raise AssertionError("invalid scope should raise HTTPException")


def test_require_debug_api_enabled_rejects_disabled_debug_surface(monkeypatch):
    monkeypatch.setattr(
        deps,
        "get_settings",
        lambda: SimpleNamespace(debug_api_enabled=False, api_key_header="X-OpenMailserver-Key"),
    )

    try:
        deps.require_debug_api_enabled()
    except HTTPException as exc:
        assert exc.status_code == status.HTTP_404_NOT_FOUND
        assert exc.detail == "Debug API is disabled"
    else:
        raise AssertionError("disabled debug API should raise HTTPException")

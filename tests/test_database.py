from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy.exc import SQLAlchemyError

from openmailserver import database


class _DummyConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, statement) -> None:
        self.statement = statement


class _HealthyEngine:
    def __init__(self) -> None:
        self.connection = _DummyConnection()

    def connect(self) -> _DummyConnection:
        return self.connection


class _BrokenEngine:
    def connect(self):
        raise SQLAlchemyError("primary unavailable")


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def test_build_engine_prefers_primary(monkeypatch):
    primary = _HealthyEngine()
    settings = SimpleNamespace(
        database_url="sqlite+pysqlite:///primary.db",
        fallback_database_url="sqlite+pysqlite:///fallback.db",
    )

    monkeypatch.setattr(database, "get_settings", lambda: settings)
    monkeypatch.setattr(database, "create_engine", lambda url, future=True: primary)

    assert database.build_engine() is primary


def test_build_engine_falls_back_when_primary_probe_fails(monkeypatch):
    fallback = _HealthyEngine()
    engines = [_BrokenEngine(), fallback]
    settings = SimpleNamespace(
        database_url="sqlite+pysqlite:///primary.db",
        fallback_database_url="sqlite+pysqlite:///fallback.db",
    )

    monkeypatch.setattr(database, "get_settings", lambda: settings)
    monkeypatch.setattr(database, "create_engine", lambda url, future=True: engines.pop(0))

    assert database.build_engine() is fallback


def test_session_scope_commits_and_closes(monkeypatch):
    session = _FakeSession()
    monkeypatch.setattr(database, "SessionLocal", lambda: session)

    with database.session_scope() as current:
        assert current is session

    assert session.committed is True
    assert session.rolled_back is False
    assert session.closed is True


def test_session_scope_rolls_back_on_error(monkeypatch):
    session = _FakeSession()
    monkeypatch.setattr(database, "SessionLocal", lambda: session)

    with pytest.raises(RuntimeError, match="boom"):
        with database.session_scope():
            raise RuntimeError("boom")

    assert session.committed is False
    assert session.rolled_back is True
    assert session.closed is True

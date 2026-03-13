from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from openmailserver.config import get_settings

LOGGER = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def build_engine(settings=None) -> Engine:
    settings = settings or get_settings()
    primary = create_engine(settings.database_url, future=True)
    try:
        with primary.connect() as conn:
            conn.execute(text("SELECT 1"))
        return primary
    except (OSError, SQLAlchemyError):
        LOGGER.warning("Primary database unavailable; falling back to configured backup database.")
        return create_engine(settings.fallback_database_url, future=True)


def init_database(settings=None, *, reset: bool = False) -> tuple[Engine, sessionmaker[Session]]:
    global _engine, _session_factory
    if reset or _engine is None or _session_factory is None:
        _engine = build_engine(settings)
        _session_factory = sessionmaker(
            bind=_engine,
            autoflush=False,
            autocommit=False,
            future=True,
        )
    return _engine, _session_factory


def get_engine() -> Engine:
    engine, _ = init_database()
    return engine


def SessionLocal() -> Session:
    _, session_factory = init_database()
    return session_factory()


def create_all(settings=None) -> None:
    from openmailserver import models  # noqa: F401

    Base.metadata.create_all(bind=get_engine() if settings is None else init_database(settings)[0])


@contextmanager
def session_scope() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

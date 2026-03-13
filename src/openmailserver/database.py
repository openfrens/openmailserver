from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from openmailserver.config import get_settings


class Base(DeclarativeBase):
    pass


def build_engine():
    settings = get_settings()
    primary = create_engine(settings.database_url, future=True)
    try:
        with primary.connect() as conn:
            conn.execute(text("SELECT 1"))
        return primary
    except Exception:
        return create_engine(settings.fallback_database_url, future=True)


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def create_all() -> None:
    from openmailserver import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


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

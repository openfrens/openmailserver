from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from openmailserver.config import get_settings
from openmailserver.database import SessionLocal
from openmailserver.models import ApiKey
from openmailserver.security import scopes_include, verify_api_key


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def require_api_key(required_scope: str):
    def dependency(
        request: Request,
        db: Session = Depends(get_db),
    ) -> ApiKey:
        api_key = request.headers.get(get_settings().api_key_header)
        if not api_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")

        keys = db.query(ApiKey).filter(ApiKey.revoked_at.is_(None)).all()
        for record in keys:
            if verify_api_key(api_key, record.key_hash) and scopes_include(
                required_scope, record.scopes
            ):
                return record
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")

    return dependency


def require_debug_api_enabled() -> None:
    if not get_settings().debug_api_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Debug API is disabled")

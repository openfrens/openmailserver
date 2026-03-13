from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, Header, HTTPException, status
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
        db: Session = Depends(get_db),
        api_key: str | None = Header(default=None, alias=get_settings().api_key_header),
    ) -> ApiKey:
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

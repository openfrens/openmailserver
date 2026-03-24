from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from openmailserver.api.router import router
from openmailserver.config import get_settings
from openmailserver.database import SessionLocal, create_all
from openmailserver.models import ApiKey
from openmailserver.security import DEFAULT_ADMIN_SCOPES, hash_api_key


def _ensure_configured_admin_key() -> None:
    settings = get_settings()
    if not settings.admin_api_key:
        return
    session = SessionLocal()
    try:
        existing = (
            session.query(ApiKey)
            .filter(
                ApiKey.key_hash == hash_api_key(settings.admin_api_key),
                ApiKey.revoked_at.is_(None),
            )
            .first()
        )
        if existing is None:
            session.add(
                ApiKey(
                    name="configured-admin",
                    key_hash=hash_api_key(settings.admin_api_key),
                    scopes=list(DEFAULT_ADMIN_SCOPES),
                )
            )
            session.commit()
    finally:
        session.close()


def build_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings = get_settings()
        app.state.settings = settings
        create_all(settings)
        _ensure_configured_admin_key()
        yield

    app = FastAPI(
        title="openmailserver",
        version="0.1.0",
        summary="Self-hostable mailserver control plane for agents.",
        lifespan=lifespan,
    )
    app.include_router(router)
    return app


app = build_app()

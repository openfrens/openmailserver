from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from openmailserver.api.router import router
from openmailserver.config import get_settings
from openmailserver.database import create_all


def build_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings = get_settings()
        app.state.settings = settings
        create_all(settings)
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

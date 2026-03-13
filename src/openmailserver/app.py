from __future__ import annotations

from fastapi import FastAPI

from openmailserver.api.router import router
from openmailserver.config import get_settings
from openmailserver.database import create_all


def build_app() -> FastAPI:
    settings = get_settings()
    create_all()
    app = FastAPI(
        title="openmailserver",
        version="0.1.0",
        summary="Self-hostable mailserver control plane for agents.",
    )
    app.state.settings = settings
    app.include_router(router)
    return app


app = build_app()

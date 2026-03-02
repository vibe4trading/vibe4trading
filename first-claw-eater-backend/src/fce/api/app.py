from __future__ import annotations

from fastapi import FastAPI

from fce.api.routes.datasets import router as datasets_router
from fce.api.routes.live import router as live_router
from fce.api.routes.me import router as me_router
from fce.api.routes.prompt_templates import router as prompt_templates_router
from fce.api.routes.runs import router as runs_router
from fce.db.engine import get_engine
from fce.db.init_db import init_db


def create_app() -> FastAPI:
    app = FastAPI(title="First Claw Eater API", version="0.1.0")

    @app.on_event("startup")
    def _startup() -> None:
        # Developer-friendly bootstrap; production should use Alembic migrations.
        init_db(get_engine())

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(me_router)
    app.include_router(live_router)
    app.include_router(datasets_router)
    app.include_router(prompt_templates_router)
    app.include_router(runs_router)

    return app


app = create_app()

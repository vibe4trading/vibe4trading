from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from v4t.api.errors import http_exception_handler
from v4t.api.routes.admin_models import router as admin_models_router
from v4t.api.routes.arena import router as arena_router
from v4t.api.routes.datasets import router as datasets_router
from v4t.api.routes.live import router as live_router
from v4t.api.routes.me import router as me_router
from v4t.api.routes.models import router as models_router
from v4t.api.routes.runs import router as runs_router
from v4t.db.engine import get_engine
from v4t.db.init_db import init_db


def create_app() -> FastAPI:
    @asynccontextmanager
    async def _lifespan(_app: FastAPI):
        init_db(get_engine())
        yield

    app = FastAPI(
        title="vibe4trading API",
        version="0.1.0",
        description="LLM trading analysis and benchmarking platform. Replay historical data, run live trading simulations, and compete in arena tournaments.",
        lifespan=_lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    @app.get("/health", tags=["Health"], summary="Health check")
    def health() -> dict[str, str]:
        """Check if the API is running."""
        return {"status": "ok"}

    app.include_router(me_router)
    app.include_router(models_router)
    app.include_router(live_router)
    app.include_router(arena_router)
    app.include_router(admin_models_router)
    app.include_router(datasets_router)
    app.include_router(runs_router)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(HTTPException, http_exception_handler)

    return app


app = create_app()

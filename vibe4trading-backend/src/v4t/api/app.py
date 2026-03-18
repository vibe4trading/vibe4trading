from __future__ import annotations

from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from v4t.api.errors import http_exception_handler
from v4t.api.routes.admin_arena import router as admin_arena_router
from v4t.api.routes.admin_model_access import router as admin_model_access_router
from v4t.api.routes.admin_models import router as admin_models_router
from v4t.api.routes.arena import router as arena_router
from v4t.api.routes.datasets import router as datasets_router
from v4t.api.routes.live import router as live_router
from v4t.api.routes.me import router as me_router
from v4t.api.routes.models import router as models_router
from v4t.api.routes.runs import router as runs_router
from v4t.auth.web import router as auth_router
from v4t.db.engine import get_engine
from v4t.db.init_db import init_db
from v4t.observability.logging import configure_logging
from v4t.settings import get_settings
from v4t.utils.tracing import init_tracing, shutdown_tracing


def create_app() -> FastAPI:
    @asynccontextmanager
    async def _lifespan(_app: FastAPI):
        configure_logging()
        settings = get_settings()
        init_tracing(
            otlp_endpoint=settings.otlp_endpoint,
            otlp_auth_header=settings.otlp_auth_header,
            project_name=settings.otlp_project_name,
            service_name="vibe4trading",
        )
        init_db(get_engine())
        yield
        shutdown_tracing()

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
    app.include_router(admin_arena_router)
    app.include_router(admin_models_router)
    app.include_router(admin_model_access_router)
    app.include_router(datasets_router)
    app.include_router(runs_router)
    app.include_router(auth_router)

    settings = get_settings()
    allowed_origins = {settings.frontend_url.rstrip("/")}
    frontend_origin = urlparse(settings.frontend_url)
    if frontend_origin.hostname in {"localhost", "127.0.0.1"}:
        scheme = frontend_origin.scheme or "http"
        port_suffix = f":{frontend_origin.port}" if frontend_origin.port else ""
        allowed_origins.update(
            {
                f"{scheme}://localhost{port_suffix}",
                f"{scheme}://127.0.0.1{port_suffix}",
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            }
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=sorted(allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(HTTPException, http_exception_handler)

    return app


app = create_app()

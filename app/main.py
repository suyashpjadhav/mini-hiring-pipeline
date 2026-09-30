"""FastAPI application factory and instance entrypoint (SYSTEM_DESIGN §3, §10.1, §16)."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.errors import register_error_handlers
from app.api.v1.candidates import router as candidates_router
from app.api.v1.health import router as health_router
from app.api.v1.search import router as search_router
from app.core.clock import Clock, SystemClock
from app.core.config import Settings, get_settings
from app.core.db import create_engine_for, run_migrations
from app.core.logging import configure_logging
from app.core.security import add_security_middleware
from app.web.routes.candidates import router as web_candidates_router
from app.web.routes.pages import router as pages_router
from app.web.routes.search import router as web_search_router


def create_app(
    settings: Settings | None = None,
    clock: Clock | None = None,
) -> FastAPI:
    """Create and configure FastAPI application instance."""
    app_settings = settings or get_settings()
    app_clock = clock or SystemClock()
    engine = create_engine_for(app_settings.database_url)

    configure_logging(level="DEBUG" if app_settings.debug else "INFO")

    @asynccontextmanager
    async def lifespan(app_instance: FastAPI) -> AsyncGenerator[None, None]:
        run_migrations(app_settings.database_url)
        yield

    app = FastAPI(
        title="Mini Hiring Pipeline",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
        lifespan=lifespan,
    )

    app.state.settings = app_settings
    app.state.clock = app_clock
    app.state.engine = engine

    app.mount("/static", StaticFiles(directory="app/web/static"), name="static")

    register_error_handlers(app)
    add_security_middleware(app, app_settings)

    app.include_router(health_router)
    app.include_router(candidates_router)
    app.include_router(search_router)
    app.include_router(web_candidates_router)
    app.include_router(web_search_router)
    app.include_router(pages_router)

    return app


app = create_app()

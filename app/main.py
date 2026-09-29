"""FastAPI application factory and instance entrypoint."""

from fastapi import FastAPI

from app.api.v1.health import router as health_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.web.routes.pages import router as pages_router


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure FastAPI application instance."""
    app_settings = settings or get_settings()
    configure_logging(level="DEBUG" if app_settings.debug else "INFO")

    app = FastAPI(
        title="Mini Hiring Pipeline",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
    )

    app.include_router(health_router)
    app.include_router(pages_router)

    return app


app = create_app()

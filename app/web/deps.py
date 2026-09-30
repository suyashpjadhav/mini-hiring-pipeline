"""FastAPI dependencies for Web page routes (SYSTEM_DESIGN §4, §10.2)."""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import Engine

from app.core.clock import Clock
from app.core.config import Settings
from app.features.pipeline.service import PipelineService


def get_settings(request: Request) -> Settings:
    """Retrieve application settings stored on app state."""
    settings: Settings = request.app.state.settings
    return settings


def get_clock(request: Request) -> Clock:
    """Retrieve application clock stored on app state."""
    clock: Clock = request.app.state.clock
    return clock


def get_engine(request: Request) -> Engine:
    """Retrieve database engine stored on app state."""
    engine: Engine = request.app.state.engine
    return engine


def get_pipeline_service(
    engine: Annotated[Engine, Depends(get_engine)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> PipelineService:
    """Provide PipelineService instance wired with state engine and clock."""
    return PipelineService(engine=engine, clock=clock)

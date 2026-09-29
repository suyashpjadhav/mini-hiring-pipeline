"""Health check API endpoint."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_pipeline_service, get_settings
from app.core.config import Settings
from app.features.pipeline.service import PipelineService

router = APIRouter(prefix="/api/v1", tags=["health"])


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: Literal["ok"]
    db: Literal["ok", "unavailable"]
    llm: Literal["enabled", "disabled"]


@router.get("/health", response_model=HealthResponse)
def get_health(
    settings: Annotated[Settings, Depends(get_settings)],
    service: Annotated[PipelineService, Depends(get_pipeline_service)],
) -> HealthResponse:
    """Get system health status including DB and LLM state."""
    db_status: Literal["ok", "unavailable"] = "ok" if service.check_db() else "unavailable"
    llm_status: Literal["enabled", "disabled"] = "enabled" if settings.llm_enabled else "disabled"
    return HealthResponse(status="ok", db=db_status, llm=llm_status)

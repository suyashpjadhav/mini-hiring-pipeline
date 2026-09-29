"""Health check API endpoint."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(prefix="/api/v1", tags=["health"])


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: Literal["ok"]
    llm: Literal["enabled", "disabled"]


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Get system health status."""
    settings = get_settings()
    llm_status: Literal["enabled", "disabled"] = "enabled" if settings.llm_enabled else "disabled"
    return HealthResponse(status="ok", llm=llm_status)

"""Public interface for the pipeline feature package (SYSTEM_DESIGN §15)."""

from app.features.pipeline.domain.stages import Action, EventType, Stage, Status
from app.features.pipeline.schemas import (
    BoardView,
    CandidateDetail,
    CandidateView,
    ChainVerification,
    EventView,
)
from app.features.pipeline.service import PipelineService

__all__ = [
    "Action",
    "BoardView",
    "CandidateDetail",
    "CandidateView",
    "ChainVerification",
    "EventType",
    "EventView",
    "PipelineService",
    "Stage",
    "Status",
]

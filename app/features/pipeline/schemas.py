"""Pydantic v2 read models for the pipeline feature (SYSTEM_DESIGN §6, §10.1)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.features.pipeline.domain.stages import EventType, Stage, Status


class CandidateView(BaseModel):
    """View model for a candidate's current state."""

    id: str
    full_name: str
    email: str | None
    stage: Stage
    status: Status
    stage_entered_at: datetime
    version: int
    time_in_stage_seconds: float | None
    last_event_at: datetime

    model_config = ConfigDict(frozen=True)


class EventView(BaseModel):
    """View model for a single audit event."""

    seq: int
    type: EventType
    from_stage: Stage | None
    to_stage: Stage | None
    occurred_at: datetime
    note: str | None
    time_spent_seconds: float | None

    model_config = ConfigDict(frozen=True)


class CandidateDetail(BaseModel):
    """View model combining candidate view, full history timeline, and chain validity."""

    candidate: CandidateView
    events: list[EventView]
    chain_valid: bool

    model_config = ConfigDict(frozen=True)


class BoardView(BaseModel):
    """View model representing the Kanban board columns."""

    applied: list[CandidateView]
    screening: list[CandidateView]
    interview: list[CandidateView]
    offer: list[CandidateView]
    hired: list[CandidateView]
    rejected: list[CandidateView]

    model_config = ConfigDict(frozen=True)


class ChainVerification(BaseModel):
    """Verification result for a candidate's hash-chain history."""

    candidate_id: str
    valid: bool
    broken_at_seq: int | None = None

    model_config = ConfigDict(frozen=True)

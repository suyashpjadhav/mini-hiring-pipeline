"""Domain event representations (SYSTEM_DESIGN §6)."""

from dataclasses import dataclass
from datetime import datetime

from app.features.pipeline.domain.stages import EventType, Stage


@dataclass(frozen=True, slots=True, kw_only=True)
class NewEvent:
    type: EventType
    from_stage: Stage | None
    to_stage: Stage | None
    note: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class StoredEvent(NewEvent):
    id: str
    candidate_id: str
    seq: int
    occurred_at: datetime  # aware UTC
    actor: str
    prev_hash: str | None
    hash: str

"""Test factories for building valid StoredEvent chains."""

from datetime import UTC, datetime, timedelta

from app.features.pipeline.domain.events import NewEvent, StoredEvent
from app.features.pipeline.domain.hashchain import compute_hash


def build_stored_event(
    new_event: NewEvent,
    *,
    candidate_id: str,
    seq: int,
    occurred_at: datetime | None = None,
    id: str | None = None,
    actor: str = "recruiter",
    prev_event: StoredEvent | None = None,
) -> StoredEvent:
    """Build a StoredEvent with valid hash and prev_hash based on previous event."""
    if occurred_at is None:
        if prev_event is not None:
            occurred_at = prev_event.occurred_at + timedelta(seconds=1)
        else:
            occurred_at = datetime(2026, 9, 29, 10, 0, 0, tzinfo=UTC)

    event_id = id or f"01H{seq:025d}"
    prev_hash = prev_event.hash if prev_event is not None else None

    # Construct event without final hash to calculate compute_hash
    draft = StoredEvent(
        type=new_event.type,
        from_stage=new_event.from_stage,
        to_stage=new_event.to_stage,
        note=new_event.note,
        id=event_id,
        candidate_id=candidate_id,
        seq=seq,
        occurred_at=occurred_at,
        actor=actor,
        prev_hash=prev_hash,
        hash="",
    )
    event_hash = compute_hash(draft)

    return StoredEvent(
        type=new_event.type,
        from_stage=new_event.from_stage,
        to_stage=new_event.to_stage,
        note=new_event.note,
        id=event_id,
        candidate_id=candidate_id,
        seq=seq,
        occurred_at=occurred_at,
        actor=actor,
        prev_hash=prev_hash,
        hash=event_hash,
    )

"""Projection of candidate state from event streams (SYSTEM_DESIGN §6)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from app.features.pipeline.domain.events import StoredEvent
from app.features.pipeline.domain.stages import REACHED_BIT, EventType, Stage, Status, next_stage


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateState:
    candidate_id: str
    stage: Stage
    status: Status
    stage_entered_at: datetime
    version: int
    reached: frozenset[Stage]
    last_event_at: datetime


def apply(state: CandidateState | None, event: StoredEvent) -> CandidateState:
    """Apply a single StoredEvent to state (or None if starting). Return new state."""
    dt = event.occurred_at
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError("StoredEvent occurred_at must be timezone-aware")

    if state is None:
        if event.type != EventType.CREATED:
            raise ValueError(f"First event must be CREATED, got {event.type}")
        if event.seq != 1:
            raise ValueError(f"First event seq must be 1, got {event.seq}")
        return CandidateState(
            candidate_id=event.candidate_id,
            stage=Stage.APPLIED,
            status=Status.ACTIVE,
            stage_entered_at=event.occurred_at,
            version=1,
            reached=frozenset({Stage.APPLIED}),
            last_event_at=event.occurred_at,
        )

    if event.candidate_id != state.candidate_id:
        raise ValueError(
            f"Event candidate_id {event.candidate_id} does not match "
            f"state candidate_id {state.candidate_id}"
        )
    if event.seq != state.version + 1:
        raise ValueError(
            f"Invalid event seq {event.seq}, expected state.version + 1 ({state.version + 1})"
        )

    if event.type == EventType.CREATED:
        raise ValueError("CREATED event cannot be applied to an existing state")

    if event.type == EventType.ADVANCED:
        if event.from_stage != state.stage:
            raise ValueError(
                f"ADVANCED event from_stage ({event.from_stage}) does not match "
                f"current state stage ({state.stage})"
            )
        target = next_stage(state.stage)
        if event.to_stage != target or event.to_stage is None:
            raise ValueError(
                f"ADVANCED event to_stage ({event.to_stage}) is invalid from stage ({state.stage})"
            )
        new_status = Status.HIRED if event.to_stage == Stage.HIRED else Status.ACTIVE
        return CandidateState(
            candidate_id=state.candidate_id,
            stage=event.to_stage,
            status=new_status,
            stage_entered_at=event.occurred_at,
            version=event.seq,
            reached=state.reached | {event.to_stage},
            last_event_at=event.occurred_at,
        )

    if event.type == EventType.REJECTED:
        if event.from_stage != state.stage:
            raise ValueError(
                f"REJECTED event from_stage ({event.from_stage}) does not match "
                f"current state stage ({state.stage})"
            )
        if event.to_stage is not None:
            raise ValueError(f"REJECTED event to_stage must be None, got {event.to_stage}")
        return CandidateState(
            candidate_id=state.candidate_id,
            stage=state.stage,
            status=Status.REJECTED,
            stage_entered_at=event.occurred_at,
            version=event.seq,
            reached=state.reached,
            last_event_at=event.occurred_at,
        )

    if event.type == EventType.NOTE:
        if event.from_stage is not None or event.to_stage is not None:
            raise ValueError("NOTE event from_stage and to_stage must be None")
        return CandidateState(
            candidate_id=state.candidate_id,
            stage=state.stage,
            status=state.status,
            stage_entered_at=state.stage_entered_at,
            version=event.seq,
            reached=state.reached,
            last_event_at=event.occurred_at,
        )

    raise ValueError(f"Unhandled event type: {event.type}")


def replay(events: Sequence[StoredEvent]) -> CandidateState:
    """Replay a sequence of events from beginning to compute current CandidateState."""
    if not events:
        raise ValueError("Cannot replay an empty sequence of events")
    state: CandidateState | None = None
    for ev in events:
        state = apply(state, ev)
    if state is None:
        raise ValueError("Replay produced empty state")
    return state


def reached_to_mask(reached: frozenset[Stage]) -> int:
    """Convert a set of reached stages into an integer bitmask."""
    mask = 0
    for stage in reached:
        mask |= REACHED_BIT[stage]
    return mask


def mask_to_reached(mask: int) -> frozenset[Stage]:
    """Convert an integer bitmask into a set of reached stages."""
    reached: set[Stage] = set()
    for stage, bit in REACHED_BIT.items():
        if mask & bit:
            reached.add(stage)
    return frozenset(reached)

"""Pipeline state machine: the single place that decides what may happen next.

Pure domain logic (SYSTEM_DESIGN §6): no I/O, no clock, no framework imports.
Callers pass the current state and the version they last saw. The machine
returns the event to append, or raises a DomainError the recruiter can read.
Clients never name a target stage; the machine computes it, so skipping is impossible.
"""

from typing import Final

from app.features.pipeline.domain.errors import (
    FinalOutcomeError,
    InvalidInputError,
    StaleVersionError,
)
from app.features.pipeline.domain.events import NewEvent
from app.features.pipeline.domain.projection import CandidateState
from app.features.pipeline.domain.stages import Action, EventType, Stage, Status, next_stage

NOTE_MAX_LEN: Final = 500


def create() -> NewEvent:
    """Every candidate starts in Applied."""
    return NewEvent(type=EventType.CREATED, from_stage=None, to_stage=Stage.APPLIED)


def decide(
    state: CandidateState,
    action: Action,
    expected_version: int,
    note: str | None = None,
) -> NewEvent:
    """Return the event produced by `action`, or raise a DomainError.

    Checks run in this order:
      1. Stale version: someone changed the candidate after the caller loaded it.
      2. Final outcome: Hired and Rejected never change.
      3. The action: advance exactly one stage, or reject from the current stage.
    """
    if expected_version != state.version:
        raise StaleVersionError(
            "This candidate changed since you loaded them.",
            hint="Refresh to see their latest stage, then try again.",
        )
    if state.status != Status.ACTIVE:
        outcome = "hired" if state.status == Status.HIRED else f"rejected at {state.stage}"
        raise FinalOutcomeError(
            f"This candidate was already {outcome}; final outcomes can't change.",
        )
    cleaned = _clean_note(note)
    if action == Action.REJECT:
        return NewEvent(
            type=EventType.REJECTED,
            from_stage=state.stage,
            to_stage=None,
            note=cleaned,
        )
    target = next_stage(state.stage)
    if target is None:  # Defensive: an active candidate is never at Hired.
        raise FinalOutcomeError("Hired is a final outcome; there is no next stage.")
    return NewEvent(
        type=EventType.ADVANCED,
        from_stage=state.stage,
        to_stage=target,
        note=cleaned,
    )


def note(text: str) -> NewEvent:
    """Record a note. Allowed at any time, including after a final outcome.

    Notes are how mistakes get corrected: history is never edited, only appended to.
    """
    cleaned = _clean_note(text)
    if cleaned is None:
        raise InvalidInputError("A note can't be empty.")
    return NewEvent(type=EventType.NOTE, from_stage=None, to_stage=None, note=cleaned)


def _clean_note(text: str | None) -> str | None:
    """Strip whitespace, turn empty into None, and enforce the length limit."""
    if text is None or not text.strip():
        return None
    cleaned = text.strip()
    if len(cleaned) > NOTE_MAX_LEN:
        raise InvalidInputError(f"Notes can be at most {NOTE_MAX_LEN} characters.")
    return cleaned

"""Unit tests for pipeline state machine (machine.py)."""

from datetime import UTC, datetime

import pytest

from app.features.pipeline.domain.errors import (
    FinalOutcomeError,
    InvalidInputError,
    StaleVersionError,
)
from app.features.pipeline.domain.machine import create, decide, note
from app.features.pipeline.domain.projection import CandidateState
from app.features.pipeline.domain.stages import Action, EventType, Stage, Status


def _make_state(
    stage: Stage = Stage.APPLIED,
    status: Status = Status.ACTIVE,
    version: int = 1,
) -> CandidateState:
    now = datetime(2026, 9, 29, 10, 0, 0, tzinfo=UTC)
    return CandidateState(
        candidate_id="cand_1",
        stage=stage,
        status=status,
        stage_entered_at=now,
        version=version,
        reached=frozenset({Stage.APPLIED}),
        last_event_at=now,
    )


def test_state_machine_transitions() -> None:
    """Every active stage can be advanced to next stage or rejected from current stage."""
    # Applied -> advance -> Screening
    st = _make_state(Stage.APPLIED)
    ev_adv = decide(st, Action.ADVANCE, expected_version=1)
    assert ev_adv.type == EventType.ADVANCED
    assert ev_adv.from_stage == Stage.APPLIED
    assert ev_adv.to_stage == Stage.SCREENING

    ev_rej = decide(st, Action.REJECT, expected_version=1)
    assert ev_rej.type == EventType.REJECTED
    assert ev_rej.from_stage == Stage.APPLIED
    assert ev_rej.to_stage is None

    # Screening -> advance -> Interview
    st = _make_state(Stage.SCREENING)
    ev_adv = decide(st, Action.ADVANCE, expected_version=1)
    assert ev_adv.to_stage == Stage.INTERVIEW

    ev_rej = decide(st, Action.REJECT, expected_version=1)
    assert ev_rej.from_stage == Stage.SCREENING

    # Interview -> advance -> Offer
    st = _make_state(Stage.INTERVIEW)
    ev_adv = decide(st, Action.ADVANCE, expected_version=1)
    assert ev_adv.to_stage == Stage.OFFER

    ev_rej = decide(st, Action.REJECT, expected_version=1)
    assert ev_rej.from_stage == Stage.INTERVIEW


def test_advance_from_offer_hires() -> None:
    """Advancing from Offer stage targets Hired stage."""
    st = _make_state(Stage.OFFER)
    ev = decide(st, Action.ADVANCE, expected_version=1)
    assert ev.type == EventType.ADVANCED
    assert ev.from_stage == Stage.OFFER
    assert ev.to_stage == Stage.HIRED

    ev_rej = decide(st, Action.REJECT, expected_version=1)
    assert ev_rej.type == EventType.REJECTED
    assert ev_rej.from_stage == Stage.OFFER
    assert ev_rej.to_stage is None


def test_final_outcome_irreversible() -> None:
    """Mutating a Hired or Rejected candidate raises FinalOutcomeError."""
    # Hired candidate
    st_hired = _make_state(Stage.HIRED, Status.HIRED)
    with pytest.raises(FinalOutcomeError, match="final outcomes can't change"):
        decide(st_hired, Action.ADVANCE, expected_version=1)
    with pytest.raises(FinalOutcomeError, match="final outcomes can't change"):
        decide(st_hired, Action.REJECT, expected_version=1)

    # Rejected candidate
    st_rej = _make_state(Stage.INTERVIEW, Status.REJECTED)
    with pytest.raises(FinalOutcomeError, match="final outcomes can't change"):
        decide(st_rej, Action.ADVANCE, expected_version=1)
    with pytest.raises(FinalOutcomeError, match="final outcomes can't change"):
        decide(st_rej, Action.REJECT, expected_version=1)


def test_stale_version_error() -> None:
    """Stale version raises StaleVersionError before final outcome check."""
    st_hired = _make_state(Stage.HIRED, Status.HIRED, version=5)
    # Stale version check happens before final outcome check
    with pytest.raises(StaleVersionError, match="changed since you loaded them"):
        decide(st_hired, Action.ADVANCE, expected_version=4)

    st_active = _make_state(Stage.APPLIED, Status.ACTIVE, version=3)
    with pytest.raises(StaleVersionError, match="changed since you loaded them"):
        decide(st_active, Action.ADVANCE, expected_version=2)


def test_note_attachment() -> None:
    """Note text is cleaned and attached to transitions when provided."""
    st = _make_state(Stage.APPLIED)
    ev = decide(st, Action.ADVANCE, expected_version=1, note=" Excellent interview! ")
    assert ev.note == "Excellent interview!"

    ev_create = create()
    assert ev_create.type == EventType.CREATED
    assert ev_create.from_stage is None
    assert ev_create.to_stage == Stage.APPLIED


def test_note_validation() -> None:
    """note() validates length and non-emptiness, and is allowed after final outcome."""
    # Empty or whitespace only -> InvalidInputError
    with pytest.raises(InvalidInputError, match="can't be empty"):
        note("")
    with pytest.raises(InvalidInputError, match="can't be empty"):
        note("   \n\t ")

    # > 500 chars -> InvalidInputError
    too_long = "a" * 501
    with pytest.raises(InvalidInputError, match="at most 500 characters"):
        note(too_long)

    # Valid note
    ev = note("Correcting candidate typo")
    assert ev.type == EventType.NOTE
    assert ev.note == "Correcting candidate typo"
    assert ev.from_stage is None
    assert ev.to_stage is None

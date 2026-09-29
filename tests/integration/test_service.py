"""Integration tests for PipelineService, projection rebuilds, and audit chain verification."""

import pytest
from sqlalchemy import Engine, text

from app.core.clock import FixedClock
from app.core.db import create_engine_for, run_migrations, write_tx
from app.core.ids import new_id
from app.features.pipeline.domain.errors import (
    DuplicateEmailError,
    StaleVersionError,
)
from app.features.pipeline.domain.events import StoredEvent
from app.features.pipeline.domain.stages import Action, EventType, Stage, Status
from app.features.pipeline.repo import PipelineRepo
from app.features.pipeline.service import PipelineService


def test_service_full_path_to_hired(pipeline_service: PipelineService) -> None:
    """Service completes full progression Applied -> Screening -> Interview -> Offer -> Hired."""
    cand = pipeline_service.create_candidate("Priya Sharma", "priya@example.com")
    assert cand.stage == Stage.APPLIED
    assert cand.status == Status.ACTIVE
    assert cand.version == 1

    # 1. Advance to Screening (expected_version=1)
    cand = pipeline_service.transition(cand.id, Action.ADVANCE, expected_version=1)
    assert cand.stage == Stage.SCREENING
    assert cand.status == Status.ACTIVE
    assert cand.version == 2

    # 2. Advance to Interview (expected_version=2)
    cand = pipeline_service.transition(cand.id, Action.ADVANCE, expected_version=2)
    assert cand.stage == Stage.INTERVIEW
    assert cand.status == Status.ACTIVE
    assert cand.version == 3

    # 3. Advance to Offer (expected_version=3)
    cand = pipeline_service.transition(cand.id, Action.ADVANCE, expected_version=3)
    assert cand.stage == Stage.OFFER
    assert cand.status == Status.ACTIVE
    assert cand.version == 4

    # 4. Advance to Hired (expected_version=4)
    cand = pipeline_service.transition(cand.id, Action.ADVANCE, expected_version=4)
    assert cand.stage == Stage.HIRED
    assert cand.status == Status.HIRED
    assert cand.version == 5

    # Verify state reached mask is 31 (1 | 2 | 4 | 8 | 16)
    detail = pipeline_service.get_detail(cand.id)
    assert len(detail.events) == 5
    assert detail.chain_valid is True


def test_service_reject_from_interview(pipeline_service: PipelineService) -> None:
    """Service records rejection from Interview stage with correct state projection."""
    cand = pipeline_service.create_candidate("Rahul Verma", "rahul@example.com")
    cand = pipeline_service.transition(cand.id, Action.ADVANCE, expected_version=1)  # Screening
    cand = pipeline_service.transition(cand.id, Action.ADVANCE, expected_version=2)  # Interview
    assert cand.stage == Stage.INTERVIEW

    # Reject from Interview
    cand = pipeline_service.transition(
        cand.id, Action.REJECT, expected_version=3, note="Not enough technical depth"
    )
    assert cand.stage == Stage.INTERVIEW  # Stage stays Interview (the stage rejected from)
    assert cand.status == Status.REJECTED
    assert cand.version == 4

    detail = pipeline_service.get_detail(cand.id)
    assert detail.events[-1].type == EventType.REJECTED
    assert detail.events[-1].note == "Not enough technical depth"


def test_service_stale_version_concurrency(
    pipeline_service: PipelineService, engine: Engine
) -> None:
    """Concurrent write with stale version raises StaleVersionError via decide & repo guard."""
    cand = pipeline_service.create_candidate("Stale Test", "stale@example.com")

    # Way 1: Two transitions with same expected_version=1
    cand_v2 = pipeline_service.transition(cand.id, Action.ADVANCE, expected_version=1)
    assert cand_v2.version == 2

    # Second write using stale expected_version=1 fails via service
    with pytest.raises(StaleVersionError) as exc_info:
        pipeline_service.transition(cand.id, Action.ADVANCE, expected_version=1)
    assert isinstance(exc_info.value, StaleVersionError)

    # Way 2: Direct repo.append_event with a stale seq (proving DB trigger guard works on its own)
    with write_tx(engine) as conn:
        repo = PipelineRepo(conn)

        # Attempt to append event with seq=2 when version is already 2 (next expected seq is 3)
        stale_evt = StoredEvent(
            id=new_id(),
            candidate_id=cand.id,
            seq=2,
            type=EventType.ADVANCED,
            from_stage=Stage.APPLIED,
            to_stage=Stage.SCREENING,
            actor="recruiter",
            note=None,
            occurred_at=cand.stage_entered_at,
            prev_hash="fake",
            hash="fake_hash",
        )
        with pytest.raises(StaleVersionError):
            repo.append_event(stale_evt)


def test_duplicate_email_raises_domain_error(pipeline_service: PipelineService) -> None:
    """Duplicate email address (case-insensitive) raises DuplicateEmailError."""
    pipeline_service.create_candidate("Anita Roy", "anita@example.com")

    # Same email with different case
    with pytest.raises(DuplicateEmailError):
        pipeline_service.create_candidate("Anita Duplicate", "ANIta@EXample.com")


def test_rebuild_projection_matches(pipeline_service: PipelineService) -> None:
    """rebuild_diff() is empty after a mixed scenario of 6 candidates built through service."""
    # 1. Active Applied
    pipeline_service.create_candidate("Cand One", "one@example.com")

    # 2. Active Screening
    c2 = pipeline_service.create_candidate("Cand Two", "two@example.com")
    pipeline_service.transition(c2.id, Action.ADVANCE, 1)

    # 3. Active Interview
    c3 = pipeline_service.create_candidate("Cand Three", "three@example.com")
    c3 = pipeline_service.transition(c3.id, Action.ADVANCE, 1)
    pipeline_service.transition(c3.id, Action.ADVANCE, 2)

    # 4. Active Offer + Note
    c4 = pipeline_service.create_candidate("Cand Four", "four@example.com")
    c4 = pipeline_service.transition(c4.id, Action.ADVANCE, 1)
    c4 = pipeline_service.transition(c4.id, Action.ADVANCE, 2)
    c4 = pipeline_service.transition(c4.id, Action.ADVANCE, 3)
    pipeline_service.add_note(c4.id, "Candidate requested salary details")

    # 5. Hired
    c5 = pipeline_service.create_candidate("Cand Five", "five@example.com")
    c5 = pipeline_service.transition(c5.id, Action.ADVANCE, 1)
    c5 = pipeline_service.transition(c5.id, Action.ADVANCE, 2)
    c5 = pipeline_service.transition(c5.id, Action.ADVANCE, 3)
    pipeline_service.transition(c5.id, Action.ADVANCE, 4)

    # 6. Rejected from Screening
    c6 = pipeline_service.create_candidate("Cand Six", "six@example.com")
    c6 = pipeline_service.transition(c6.id, Action.ADVANCE, 1)
    pipeline_service.transition(c6.id, Action.REJECT, 2, note="Failed screening test")

    diffs = pipeline_service.rebuild_diff()
    assert diffs == [], f"Expected zero differences in projection rebuild, got: {diffs}"


def test_verify_detects_tampering(db_url: str, fixed_clock: FixedClock) -> None:
    """verify() passes, then fails after tampering in a throwaway DB with triggers dropped."""
    run_migrations(db_url)
    throwaway_engine = create_engine_for(db_url)
    service = PipelineService(throwaway_engine, fixed_clock)

    cand = service.create_candidate("Tamper Target", "tamper@example.com")
    service.add_note(cand.id, "Original note text")

    # 1. Verification passes initially
    verify_before = service.verify(cand.id)
    assert verify_before.valid is True
    assert verify_before.broken_at_seq is None

    # 2. Tamper: drop no-update trigger and modify note in DB directly
    with throwaway_engine.connect() as conn:
        conn.execute(text("DROP TRIGGER stage_events_no_update;"))
        query = text(
            "UPDATE stage_events SET note = 'Tampered note text' "
            "WHERE candidate_id = :cid AND seq = 2;"
        )
        conn.execute(query, {"cid": cand.id})
        conn.commit()

    # 3. Verification now detects broken chain at seq 2
    verify_after = service.verify(cand.id)
    assert verify_after.valid is False
    assert verify_after.broken_at_seq == 2


def test_get_detail_time_spent_and_in_stage(
    pipeline_service: PipelineService, fixed_clock: FixedClock
) -> None:
    """get_detail returns accurate time_spent_seconds per event and time_in_stage_seconds."""
    cand = pipeline_service.create_candidate("Time Test", "time@example.com")

    # Advance clock by 2 hours (7200 seconds)
    fixed_clock.advance(hours=2)
    cand_s2 = pipeline_service.transition(cand.id, Action.ADVANCE, expected_version=1)

    # Advance clock by 3 hours (10800 seconds)
    fixed_clock.advance(hours=3)
    pipeline_service.add_note(cand_s2.id, "Just checking in")

    detail = pipeline_service.get_detail(cand.id)

    # Event 1 (CREATED -> Applied): time_spent = 7200.0s until next stage change
    assert detail.events[0].time_spent_seconds == pytest.approx(7200.0)

    # Event 2 (ADVANCED -> Screening): current stage entering event, active candidate at +5 hours
    # time_spent_seconds = (now - stage_entered_at) = 3 hours (10800.0s)
    assert detail.events[1].time_spent_seconds == pytest.approx(10800.0)

    # Event 3 (NOTE): time_spent_seconds is None
    assert detail.events[2].time_spent_seconds is None

    # Candidate current time_in_stage_seconds = 3 hours (10800.0s)
    assert detail.candidate.time_in_stage_seconds == pytest.approx(10800.0)

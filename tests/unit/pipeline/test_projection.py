"""Unit tests for pipeline projection rules (projection.py)."""

from datetime import UTC, datetime, timedelta
from functools import reduce

import pytest

from app.features.pipeline.domain.events import NewEvent
from app.features.pipeline.domain.machine import create, decide, note
from app.features.pipeline.domain.projection import (
    apply,
    mask_to_reached,
    reached_to_mask,
    replay,
)
from app.features.pipeline.domain.stages import STAGE_ORDER, Action, EventType, Stage, Status
from tests.unit.pipeline.factories import build_stored_event


def test_apply_rules() -> None:
    """Each apply rule produces correct CandidateState."""
    t0 = datetime(2026, 9, 29, 10, 0, 0, tzinfo=UTC)

    # CREATED
    ev_created = build_stored_event(create(), candidate_id="cand_1", seq=1, occurred_at=t0)
    st1 = apply(None, ev_created)
    assert st1.candidate_id == "cand_1"
    assert st1.stage == Stage.APPLIED
    assert st1.status == Status.ACTIVE
    assert st1.stage_entered_at == t0
    assert st1.version == 1
    assert st1.reached == frozenset({Stage.APPLIED})
    assert st1.last_event_at == t0

    # ADVANCED
    t1 = t0 + timedelta(hours=1)
    ev_adv = build_stored_event(
        decide(st1, Action.ADVANCE, expected_version=1),
        candidate_id="cand_1",
        seq=2,
        occurred_at=t1,
        prev_event=ev_created,
    )
    st2 = apply(st1, ev_adv)
    assert st2.stage == Stage.SCREENING
    assert st2.status == Status.ACTIVE
    assert st2.stage_entered_at == t1
    assert st2.version == 2
    assert st2.reached == frozenset({Stage.APPLIED, Stage.SCREENING})
    assert st2.last_event_at == t1


def test_rejected_keeps_stage_and_sets_entered_at() -> None:
    """REJECTED keeps the stage intact and sets stage_entered_at to the rejection time."""
    t0 = datetime(2026, 9, 29, 10, 0, 0, tzinfo=UTC)
    ev_created = build_stored_event(create(), candidate_id="cand_1", seq=1, occurred_at=t0)
    st1 = apply(None, ev_created)

    t1 = t0 + timedelta(days=2)
    ev_rej = build_stored_event(
        decide(st1, Action.REJECT, expected_version=1),
        candidate_id="cand_1",
        seq=2,
        occurred_at=t1,
        prev_event=ev_created,
    )
    st2 = apply(st1, ev_rej)

    assert st2.status == Status.REJECTED
    assert st2.stage == Stage.APPLIED  # stage UNCHANGED
    assert st2.stage_entered_at == t1  # set to rejection time
    assert st2.version == 2
    assert st2.reached == frozenset({Stage.APPLIED})
    assert st2.last_event_at == t1


def test_note_updates_version_and_last_event_at() -> None:
    """NOTE event updates version and last_event_at, leaving stage and status unchanged.

    SEARCH_SPEC §10 item 5 ('Else -> last_event_at DESC') defines last_event_at as tracking the
    timestamp of the most recent candidate activity. A note is recruiter activity on the candidate,
    so last_event_at updates to event.occurred_at.
    """
    t0 = datetime(2026, 9, 29, 10, 0, 0, tzinfo=UTC)
    ev_created = build_stored_event(create(), candidate_id="cand_1", seq=1, occurred_at=t0)
    st1 = apply(None, ev_created)

    t1 = t0 + timedelta(hours=3)
    ev_note = build_stored_event(
        note("Spoke on phone"),
        candidate_id="cand_1",
        seq=2,
        occurred_at=t1,
        prev_event=ev_created,
    )
    st2 = apply(st1, ev_note)

    assert st2.version == 2
    assert st2.last_event_at == t1
    assert st2.stage == st1.stage
    assert st2.status == st1.status
    assert st2.stage_entered_at == st1.stage_entered_at
    assert st2.reached == st1.reached


def test_mask_round_trip() -> None:
    """mask_to_reached(reached_to_mask(reached)) round-trips for all 32 subsets of STAGE_ORDER."""
    from itertools import combinations

    for r in range(len(STAGE_ORDER) + 1):
        for combo in combinations(STAGE_ORDER, r):
            reached = frozenset(combo)
            mask = reached_to_mask(reached)
            assert 0 <= mask <= 31
            restored = mask_to_reached(mask)
            assert restored == reached


def test_apply_value_errors() -> None:
    """Internal invariant violations raise ValueError (not DomainError)."""
    t0 = datetime(2026, 9, 29, 10, 0, 0, tzinfo=UTC)

    # 1. Non-CREATED event on None state
    ev_adv = build_stored_event(
        NewEvent(type=EventType.ADVANCED, from_stage=Stage.APPLIED, to_stage=Stage.SCREENING),
        candidate_id="c1",
        seq=1,
        occurred_at=t0,
    )
    with pytest.raises(ValueError, match="First event must be CREATED"):
        apply(None, ev_adv)

    # 2. CREATED with seq != 1
    ev_created2 = build_stored_event(create(), candidate_id="c1", seq=2, occurred_at=t0)
    with pytest.raises(ValueError, match="First event seq must be 1"):
        apply(None, ev_created2)

    # 3. CREATED applied to existing state
    ev_created1 = build_stored_event(create(), candidate_id="c1", seq=1, occurred_at=t0)
    st1 = apply(None, ev_created1)
    with pytest.raises(ValueError, match="CREATED event cannot be applied"):
        apply(st1, ev_created2)

    # 4. Wrong sequence number
    t1 = t0 + timedelta(minutes=5)
    ev_seq_wrong = build_stored_event(
        decide(st1, Action.ADVANCE, expected_version=1),
        candidate_id="c1",
        seq=3,
        occurred_at=t1,
        prev_event=ev_created1,
    )
    with pytest.raises(ValueError, match=r"Invalid event seq 3, expected state\.version \+ 1"):
        apply(st1, ev_seq_wrong)

    # 5. Candidate ID mismatch
    ev_diff_cand = build_stored_event(
        decide(st1, Action.ADVANCE, expected_version=1),
        candidate_id="c2",
        seq=2,
        occurred_at=t1,
        prev_event=ev_created1,
    )
    with pytest.raises(ValueError, match="does not match state candidate_id"):
        apply(st1, ev_diff_cand)


def test_replay_equals_fold_apply() -> None:
    """replay(events) equals left fold reduce(apply, events). Empty sequence raises ValueError."""
    with pytest.raises(ValueError, match="Cannot replay an empty sequence"):
        replay([])

    t0 = datetime(2026, 9, 29, 10, 0, 0, tzinfo=UTC)
    e1 = build_stored_event(create(), candidate_id="cand_1", seq=1, occurred_at=t0)
    st1 = apply(None, e1)

    t1 = t0 + timedelta(hours=1)
    e2 = build_stored_event(
        decide(st1, Action.ADVANCE, expected_version=1),
        candidate_id="cand_1",
        seq=2,
        occurred_at=t1,
        prev_event=e1,
    )

    t2 = t1 + timedelta(hours=1)
    e3 = build_stored_event(
        note("Call completed"),
        candidate_id="cand_1",
        seq=3,
        occurred_at=t2,
        prev_event=e2,
    )

    events = [e1, e2, e3]
    replayed_state = replay(events)
    folded_state = reduce(apply, events, None)

    assert replayed_state == folded_state
    assert replayed_state.version == 3
    assert replayed_state.stage == Stage.SCREENING

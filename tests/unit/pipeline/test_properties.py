"""Property-based tests for pipeline state machine and projection invariants using Hypothesis."""

from contextlib import suppress
from datetime import UTC, datetime, timedelta

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.features.pipeline.domain.errors import FinalOutcomeError, InvalidInputError
from app.features.pipeline.domain.events import StoredEvent
from app.features.pipeline.domain.machine import create, decide, note
from app.features.pipeline.domain.projection import CandidateState, apply
from app.features.pipeline.domain.stages import (
    STAGE_ORDER,
    Action,
    EventType,
    Stage,
    Status,
    next_stage,
)
from tests.unit.pipeline.factories import build_stored_event


@settings(
    max_examples=300,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(st.data())
def test_property_machine_invariants(data: st.DataObject) -> None:
    """Random sequences of {advance, reject, note} maintain domain invariants:
    - Every ADVANCED goes to next_stage(from_stage)
    - After a final outcome, every advance or reject raises FinalOutcomeError
    - version == len(events)
    - reached is always a prefix of STAGE_ORDER
    - status is hired ⇔ stage is Hired
    """
    t0 = datetime(2026, 9, 29, 10, 0, 0, tzinfo=UTC)
    cand_id = "cand_hypothesis"

    # Start candidate in Applied via create()
    ev_created = build_stored_event(create(), candidate_id=cand_id, seq=1, occurred_at=t0)
    state: CandidateState = apply(None, ev_created)
    events: list[StoredEvent] = [ev_created]

    # Generate up to 15 actions
    num_actions = data.draw(st.integers(min_value=0, max_value=15))

    action_type_strategy = st.sampled_from(["advance", "reject", "note"])
    note_text_strategy = st.sampled_from(
        ["Interview went well", "   ", "Correction note", "Follow up tomorrow"]
    )

    prev_event = ev_created

    for _ in range(num_actions):
        act_kind = data.draw(action_type_strategy)
        current_time = prev_event.occurred_at + timedelta(seconds=1)

        if act_kind == "advance":
            if state.status != Status.ACTIVE:
                try:
                    decide(state, Action.ADVANCE, expected_version=state.version)
                except FinalOutcomeError:
                    pass
                else:
                    msg = "Expected FinalOutcomeError when advancing non-active candidate"
                    raise AssertionError(msg)
                continue

            # Active candidate advancing
            expected_next = next_stage(state.stage)
            new_ev = decide(state, Action.ADVANCE, expected_version=state.version)
            assert new_ev.type == EventType.ADVANCED
            assert new_ev.from_stage == state.stage
            assert new_ev.to_stage == expected_next

            stored = build_stored_event(
                new_ev,
                candidate_id=cand_id,
                seq=len(events) + 1,
                occurred_at=current_time,
                prev_event=prev_event,
            )
            state = apply(state, stored)
            events.append(stored)
            prev_event = stored

        elif act_kind == "reject":
            if state.status != Status.ACTIVE:
                try:
                    decide(state, Action.REJECT, expected_version=state.version)
                except FinalOutcomeError:
                    pass
                else:
                    msg = "Expected FinalOutcomeError when rejecting non-active candidate"
                    raise AssertionError(msg)
                continue

            # Active candidate rejecting
            new_ev = decide(state, Action.REJECT, expected_version=state.version)
            assert new_ev.type == EventType.REJECTED
            assert new_ev.from_stage == state.stage
            assert new_ev.to_stage is None

            stored = build_stored_event(
                new_ev,
                candidate_id=cand_id,
                seq=len(events) + 1,
                occurred_at=current_time,
                prev_event=prev_event,
            )
            state = apply(state, stored)
            events.append(stored)
            prev_event = stored

        elif act_kind == "note":
            note_text = data.draw(note_text_strategy)
            if not note_text.strip():
                with suppress(InvalidInputError):
                    note(note_text)
                continue

            new_ev = note(note_text)
            stored = build_stored_event(
                new_ev,
                candidate_id=cand_id,
                seq=len(events) + 1,
                occurred_at=current_time,
                prev_event=prev_event,
            )
            state = apply(state, stored)
            events.append(stored)
            prev_event = stored

        # --- Invariant Checks after every step ---

        # 1. version == number of events
        assert state.version == len(events)

        # 2. status is hired ⇔ stage is Hired
        assert (state.status == Status.HIRED) == (state.stage == Stage.HIRED)

        # 3. reached is always a prefix of STAGE_ORDER
        reached_sorted = sorted(state.reached, key=lambda s: STAGE_ORDER.index(s))
        expected_prefix = STAGE_ORDER[: len(reached_sorted)]
        assert tuple(reached_sorted) == expected_prefix

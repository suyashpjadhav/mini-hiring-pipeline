"""Unit tests for hash chain generation and verification (hashchain.py)."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from app.features.pipeline.domain.hashchain import (
    canonical_json,
    compute_hash,
    verify_chain,
)
from app.features.pipeline.domain.machine import create, decide, note
from app.features.pipeline.domain.projection import apply
from app.features.pipeline.domain.stages import Action, Stage
from tests.unit.pipeline.factories import build_stored_event


def test_canonical_json_stability() -> None:
    """canonical_json excludes prev_hash and hash, orders keys, and is deterministic."""
    t0 = datetime(2026, 9, 29, 10, 0, 0, tzinfo=UTC)
    e1 = build_stored_event(create(), candidate_id="cand_1", seq=1, occurred_at=t0)

    cj1 = canonical_json(e1)
    # Re-running produces identical canonical JSON
    assert canonical_json(e1) == cj1
    assert "prev_hash" not in cj1
    assert '"hash"' not in cj1
    assert '"actor":"recruiter"' in cj1
    assert '"candidate_id":"cand_1"' in cj1


def test_valid_chain_verifies() -> None:
    """A valid event chain passes verify_chain."""
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
    st2 = apply(st1, e2)
    assert st2.stage == Stage.SCREENING

    t2 = t1 + timedelta(hours=1)
    e3 = build_stored_event(
        note("Great resume"),
        candidate_id="cand_1",
        seq=3,
        occurred_at=t2,
        prev_event=e2,
    )

    result = verify_chain([e1, e2, e3])
    assert result.valid is True
    assert result.broken_at_seq is None


def test_verify_chain_detects_tampering() -> None:
    """Tampering each field individually (note, to_stage, occurred_at, seq, actor) -> detected."""
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
        note("Original note"),
        candidate_id="cand_1",
        seq=3,
        occurred_at=t2,
        prev_event=e2,
    )

    chain = [e1, e2, e3]
    assert verify_chain(chain).valid is True

    # Tamper note on event 3
    t_note = replace(e3, note="Tampered note")
    res = verify_chain([e1, e2, t_note])
    assert res.valid is False
    assert res.broken_at_seq == 3

    # Tamper to_stage on event 2
    t_stage = replace(e2, to_stage=Stage.HIRED)
    res = verify_chain([e1, t_stage, e3])
    assert res.valid is False
    assert res.broken_at_seq == 2

    # Tamper occurred_at on event 2
    t_time = replace(e2, occurred_at=t1 + timedelta(days=1))
    res = verify_chain([e1, t_time, e3])
    assert res.valid is False
    assert res.broken_at_seq == 2

    # Tamper seq on event 2
    t_seq = replace(e2, seq=99)
    res = verify_chain([e1, t_seq, e3])
    assert res.valid is False
    assert res.broken_at_seq == 99

    # Tamper actor on event 1
    t_actor = replace(e1, actor="malicious_actor")
    res = verify_chain([t_actor, e2, e3])
    assert res.valid is False
    assert res.broken_at_seq == 1


def test_broken_prev_hash_detected() -> None:
    """A broken prev_hash link is detected by verify_chain."""
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

    # Break prev_hash on event 2
    bad_prev = replace(e2, prev_hash="bad_hash_value")
    broken_e2 = replace(bad_prev, hash=compute_hash(bad_prev))
    res = verify_chain([e1, broken_e2])
    assert res.valid is False
    assert res.broken_at_seq == 2


def test_deleted_middle_event_detected() -> None:
    """Deleting an event in the middle of a chain is detected."""
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
        note("Third event"),
        candidate_id="cand_1",
        seq=3,
        occurred_at=t2,
        prev_event=e2,
    )

    # Delete e2 (chain is now e1, e3)
    res = verify_chain([e1, e3])
    assert res.valid is False
    assert res.broken_at_seq == 3

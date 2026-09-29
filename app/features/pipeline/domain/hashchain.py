"""Tamper-evident hash chain for domain events (SYSTEM_DESIGN §9 layer 4)."""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass

from app.core.timeutil import to_epoch_ms
from app.features.pipeline.domain.events import StoredEvent


def canonical_json(event: StoredEvent) -> str:
    """Produce deterministic canonical JSON representation of a StoredEvent."""
    d = {
        "actor": event.actor,
        "candidate_id": event.candidate_id,
        "from_stage": event.from_stage.value if event.from_stage is not None else None,
        "id": event.id,
        "note": event.note,
        "occurred_at": to_epoch_ms(event.occurred_at),
        "seq": event.seq,
        "to_stage": event.to_stage.value if event.to_stage is not None else None,
        "type": event.type.value,
    }
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_hash(event: StoredEvent) -> str:
    """Compute the SHA-256 hex hash of an event given prev_hash and canonical JSON."""
    payload = (event.prev_hash or "") + canonical_json(event)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True, kw_only=True)
class ChainVerification:
    valid: bool
    broken_at_seq: int | None = None


def verify_chain(events: Sequence[StoredEvent]) -> ChainVerification:
    """Verify sequence numbers, prev_hash linkage, and hash integrity of an event stream."""
    if not events:
        return ChainVerification(valid=True, broken_at_seq=None)

    expected_seq = 1
    prev_hash: str | None = None

    for event in events:
        if event.seq != expected_seq:
            return ChainVerification(valid=False, broken_at_seq=event.seq)

        if expected_seq == 1:
            if event.prev_hash is not None:
                return ChainVerification(valid=False, broken_at_seq=event.seq)
        else:
            if event.prev_hash != prev_hash:
                return ChainVerification(valid=False, broken_at_seq=event.seq)

        expected_hash = compute_hash(event)
        if event.hash != expected_hash:
            return ChainVerification(valid=False, broken_at_seq=event.seq)

        prev_hash = event.hash
        expected_seq += 1

    return ChainVerification(valid=True, broken_at_seq=None)

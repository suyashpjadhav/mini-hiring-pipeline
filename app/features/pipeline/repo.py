"""Pipeline database repository (SYSTEM_DESIGN §7, §8, §15).

This is the ONLY module with SQL queries for the pipeline domain.
Converts epoch ms <-> datetime and mask <-> frozenset at this boundary only.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import insert, select, update
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

from app.core.tables import candidate_state, candidates, stage_events
from app.core.timeutil import from_epoch_ms, to_epoch_ms
from app.features.pipeline.domain.errors import DuplicateEmailError, StaleVersionError
from app.features.pipeline.domain.events import StoredEvent
from app.features.pipeline.domain.projection import (
    CandidateState,
    mask_to_reached,
    reached_to_mask,
)
from app.features.pipeline.domain.stages import EventType, Stage, Status


def _map_integrity_error(err: IntegrityError) -> None:
    msg = str(err)
    if "UNIQUE constraint failed: stage_events.candidate_id, stage_events.seq" in msg:
        raise StaleVersionError(
            "The candidate was modified by another operation.",
            hint="Please refresh and try again.",
        ) from err
    if "transition does not match current state" in msg:
        raise StaleVersionError(
            "The candidate's stage or version has changed.",
            hint="Please refresh and try again.",
        ) from err
    if "UNIQUE constraint failed: candidates.email" in msg:
        raise DuplicateEmailError(
            "A candidate with this email address already exists.",
            hint="Please check the email address or use a different one.",
        ) from err
    raise err


class PipelineRepo:
    """Repository handling SQL persistence for candidates, stage_events, and candidate_state."""

    def __init__(self, conn: Connection) -> None:
        self.conn = conn

    def insert_candidate(
        self,
        candidate_id: str,
        full_name: str,
        name_normalized: str,
        email: str | None,
        created_at: datetime,
    ) -> None:
        """Insert a candidate record into the database."""
        stmt = insert(candidates).values(
            id=candidate_id,
            full_name=full_name,
            name_normalized=name_normalized,
            email=email,
            created_at=to_epoch_ms(created_at),
        )
        try:
            self.conn.execute(stmt)
        except IntegrityError as err:
            _map_integrity_error(err)

    def append_event(self, event: StoredEvent) -> None:
        """Append a new StoredEvent to stage_events table."""
        stmt = insert(stage_events).values(
            id=event.id,
            candidate_id=event.candidate_id,
            seq=event.seq,
            type=event.type.value,
            from_stage=event.from_stage.value if event.from_stage else None,
            to_stage=event.to_stage.value if event.to_stage else None,
            occurred_at=to_epoch_ms(event.occurred_at),
            actor=event.actor,
            note=event.note,
            prev_hash=event.prev_hash,
            hash=event.hash,
        )
        try:
            self.conn.execute(stmt)
        except IntegrityError as err:
            _map_integrity_error(err)

    def insert_state(self, state: CandidateState) -> None:
        """Insert initial CandidateState into candidate_state table."""
        stmt = insert(candidate_state).values(
            candidate_id=state.candidate_id,
            stage=state.stage.value,
            status=state.status.value,
            stage_entered_at=to_epoch_ms(state.stage_entered_at),
            version=state.version,
            reached_mask=reached_to_mask(state.reached),
            last_event_at=to_epoch_ms(state.last_event_at),
        )
        try:
            self.conn.execute(stmt)
        except IntegrityError as err:
            _map_integrity_error(err)

    def update_state(self, state: CandidateState) -> None:
        """Update CandidateState projection in candidate_state table."""
        stmt = (
            update(candidate_state)
            .where(candidate_state.c.candidate_id == state.candidate_id)
            .values(
                stage=state.stage.value,
                status=state.status.value,
                stage_entered_at=to_epoch_ms(state.stage_entered_at),
                version=state.version,
                reached_mask=reached_to_mask(state.reached),
                last_event_at=to_epoch_ms(state.last_event_at),
            )
        )
        try:
            self.conn.execute(stmt)
        except IntegrityError as err:
            _map_integrity_error(err)

    def get_state(self, candidate_id: str) -> CandidateState | None:
        """Fetch current CandidateState by candidate_id."""
        stmt = select(candidate_state).where(candidate_state.c.candidate_id == candidate_id)
        row = self.conn.execute(stmt).mappings().first()
        if not row:
            return None
        return CandidateState(
            candidate_id=row["candidate_id"],
            stage=Stage(row["stage"]),
            status=Status(row["status"]),
            stage_entered_at=from_epoch_ms(row["stage_entered_at"]),
            version=row["version"],
            reached=mask_to_reached(row["reached_mask"]),
            last_event_at=from_epoch_ms(row["last_event_at"]),
        )

    def get_candidate(self, candidate_id: str) -> dict[str, Any] | None:
        """Fetch raw candidate metadata dictionary by candidate_id."""
        stmt = select(candidates).where(candidates.c.id == candidate_id)
        row = self.conn.execute(stmt).mappings().first()
        if not row:
            return None
        return {
            "id": row["id"],
            "full_name": row["full_name"],
            "name_normalized": row["name_normalized"],
            "email": row["email"],
            "created_at": from_epoch_ms(row["created_at"]),
        }

    def get_events(self, candidate_id: str) -> list[StoredEvent]:
        """Fetch all events for candidate ordered by seq ascending."""
        stmt = (
            select(stage_events)
            .where(stage_events.c.candidate_id == candidate_id)
            .order_by(stage_events.c.seq.asc())
        )
        rows = self.conn.execute(stmt).mappings().all()
        events: list[StoredEvent] = []
        for r in rows:
            events.append(
                StoredEvent(
                    id=r["id"],
                    candidate_id=r["candidate_id"],
                    seq=r["seq"],
                    type=EventType(r["type"]),
                    from_stage=Stage(r["from_stage"]) if r["from_stage"] else None,
                    to_stage=Stage(r["to_stage"]) if r["to_stage"] else None,
                    occurred_at=from_epoch_ms(r["occurred_at"]),
                    actor=r["actor"],
                    note=r["note"],
                    prev_hash=r["prev_hash"],
                    hash=r["hash"],
                )
            )
        return events

    def last_event(self, candidate_id: str) -> StoredEvent | None:
        """Fetch candidate's most recent StoredEvent by seq descending."""
        stmt = (
            select(stage_events)
            .where(stage_events.c.candidate_id == candidate_id)
            .order_by(stage_events.c.seq.desc())
            .limit(1)
        )
        r = self.conn.execute(stmt).mappings().first()
        if not r:
            return None
        return StoredEvent(
            id=r["id"],
            candidate_id=r["candidate_id"],
            seq=r["seq"],
            type=EventType(r["type"]),
            from_stage=Stage(r["from_stage"]) if r["from_stage"] else None,
            to_stage=Stage(r["to_stage"]) if r["to_stage"] else None,
            occurred_at=from_epoch_ms(r["occurred_at"]),
            actor=r["actor"],
            note=r["note"],
            prev_hash=r["prev_hash"],
            hash=r["hash"],
        )

    def list_board_rows(self) -> list[dict[str, Any]]:
        """List candidates JOIN candidate_state for board rendering."""
        j = candidates.join(candidate_state, candidates.c.id == candidate_state.c.candidate_id)
        stmt = select(
            candidates.c.id,
            candidates.c.full_name,
            candidates.c.name_normalized,
            candidates.c.email,
            candidates.c.created_at,
            candidate_state.c.stage,
            candidate_state.c.status,
            candidate_state.c.stage_entered_at,
            candidate_state.c.version,
            candidate_state.c.reached_mask,
            candidate_state.c.last_event_at,
        ).select_from(j)
        rows = self.conn.execute(stmt).mappings().all()
        results: list[dict[str, Any]] = []
        for r in rows:
            results.append(
                {
                    "id": r["id"],
                    "full_name": r["full_name"],
                    "name_normalized": r["name_normalized"],
                    "email": r["email"],
                    "created_at": from_epoch_ms(r["created_at"]),
                    "state": CandidateState(
                        candidate_id=r["id"],
                        stage=Stage(r["stage"]),
                        status=Status(r["status"]),
                        stage_entered_at=from_epoch_ms(r["stage_entered_at"]),
                        version=r["version"],
                        reached=mask_to_reached(r["reached_mask"]),
                        last_event_at=from_epoch_ms(r["last_event_at"]),
                    ),
                }
            )
        return results

    def list_candidate_ids(self) -> list[str]:
        """List all candidate IDs ordered by creation time."""
        stmt = select(candidates.c.id).order_by(candidates.c.created_at.asc())
        return list(self.conn.execute(stmt).scalars().all())

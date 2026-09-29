"""Pipeline service layer owning business transactions (SYSTEM_DESIGN §4, §8, §15)."""

import dataclasses
from typing import Any

from sqlalchemy import Engine

from app.core.clock import Clock
from app.core.db import read_tx, write_tx
from app.core.ids import new_id
from app.core.text import clean_display_name, normalize_name
from app.features.pipeline.domain import hashchain, machine, projection
from app.features.pipeline.domain.errors import InvalidInputError, NotFoundError
from app.features.pipeline.domain.events import StoredEvent
from app.features.pipeline.domain.projection import CandidateState
from app.features.pipeline.domain.stages import Action, EventType, Stage, Status
from app.features.pipeline.repo import PipelineRepo
from app.features.pipeline.schemas import (
    BoardView,
    CandidateDetail,
    CandidateView,
    ChainVerification,
    EventView,
)


class PipelineService:
    """Service layer for hiring pipeline operations."""

    def __init__(self, engine: Engine, clock: Clock) -> None:
        self.engine = engine
        self.clock = clock

    def create_candidate(self, full_name: str, email: str | None = None) -> CandidateView:
        """Create a new candidate in Applied stage."""
        try:
            clean_name = clean_display_name(full_name)
        except ValueError as err:
            raise InvalidInputError(str(err)) from err

        norm_name = normalize_name(clean_name)
        clean_email = email.strip().lower() if email and email.strip() else None

        now = self.clock.now()
        cand_id = new_id()
        event_id = new_id()

        dummy_event = StoredEvent(
            id=event_id,
            candidate_id=cand_id,
            seq=1,
            type=EventType.CREATED,
            from_stage=None,
            to_stage=Stage.APPLIED,
            actor="recruiter",
            note=None,
            occurred_at=now,
            prev_hash=None,
            hash="",
        )
        event_hash = hashchain.compute_hash(dummy_event)
        created_event = dataclasses.replace(dummy_event, hash=event_hash)
        initial_state = projection.apply(None, created_event)

        with write_tx(self.engine) as conn:
            repo = PipelineRepo(conn)
            repo.insert_candidate(
                candidate_id=cand_id,
                full_name=clean_name,
                name_normalized=norm_name,
                email=clean_email,
                created_at=now,
            )
            repo.append_event(created_event)
            repo.insert_state(initial_state)

        return self._make_candidate_view(initial_state, clean_name, clean_email, now)

    def transition(
        self,
        candidate_id: str,
        action: Action,
        expected_version: int,
        note: str | None = None,
    ) -> CandidateView:
        """Transition candidate state (advance or reject)."""
        now = self.clock.now()

        with write_tx(self.engine) as conn:
            repo = PipelineRepo(conn)
            state = repo.get_state(candidate_id)
            if state is None:
                raise NotFoundError(f"Candidate '{candidate_id}' not found")

            new_evt = machine.decide(state, action, expected_version, note)
            last_evt = repo.last_event(candidate_id)
            prev_hash = last_evt.hash if last_evt else None

            event_id = new_id()
            dummy_event = StoredEvent(
                id=event_id,
                candidate_id=candidate_id,
                seq=state.version + 1,
                type=new_evt.type,
                from_stage=new_evt.from_stage,
                to_stage=new_evt.to_stage,
                actor="recruiter",
                note=new_evt.note,
                occurred_at=now,
                prev_hash=prev_hash,
                hash="",
            )
            event_hash = hashchain.compute_hash(dummy_event)
            stored_event = dataclasses.replace(dummy_event, hash=event_hash)

            # Append the event FIRST to the event store
            repo.append_event(stored_event)

            # Then compute and update candidate state projection
            new_state = projection.apply(state, stored_event)
            repo.update_state(new_state)

            cand = repo.get_candidate(candidate_id)
            full_name = cand["full_name"] if cand else ""
            email = cand["email"] if cand else None

        return self._make_candidate_view(new_state, full_name, email, now)

    def add_note(self, candidate_id: str, text: str) -> CandidateView:
        """Add a NOTE correction/annotation event for candidate."""
        if not text or not text.strip():
            raise InvalidInputError("Note text cannot be empty")

        now = self.clock.now()

        with write_tx(self.engine) as conn:
            repo = PipelineRepo(conn)
            state = repo.get_state(candidate_id)
            if state is None:
                raise NotFoundError(f"Candidate '{candidate_id}' not found")

            try:
                new_evt = machine.note(text)
            except ValueError as err:
                raise InvalidInputError(str(err)) from err

            last_evt = repo.last_event(candidate_id)
            prev_hash = last_evt.hash if last_evt else None

            event_id = new_id()
            dummy_event = StoredEvent(
                id=event_id,
                candidate_id=candidate_id,
                seq=state.version + 1,
                type=new_evt.type,
                from_stage=new_evt.from_stage,
                to_stage=new_evt.to_stage,
                actor="recruiter",
                note=new_evt.note,
                occurred_at=now,
                prev_hash=prev_hash,
                hash="",
            )
            event_hash = hashchain.compute_hash(dummy_event)
            stored_event = dataclasses.replace(dummy_event, hash=event_hash)

            # Append the event FIRST to the event store
            repo.append_event(stored_event)

            # Then compute and update candidate state projection
            new_state = projection.apply(state, stored_event)
            repo.update_state(new_state)

            cand = repo.get_candidate(candidate_id)
            full_name = cand["full_name"] if cand else ""
            email = cand["email"] if cand else None

        return self._make_candidate_view(new_state, full_name, email, now)

    def get_detail(self, candidate_id: str) -> CandidateDetail:
        """Get candidate details including full timeline and audit verification."""
        now = self.clock.now()

        with read_tx(self.engine) as conn:
            repo = PipelineRepo(conn)
            state = repo.get_state(candidate_id)
            cand = repo.get_candidate(candidate_id)
            if state is None or cand is None:
                raise NotFoundError(f"Candidate '{candidate_id}' not found")

            events = repo.get_events(candidate_id)

        chain_verification = hashchain.verify_chain(events)
        cand_view = self._make_candidate_view(state, cand["full_name"], cand["email"], now)

        event_views: list[EventView] = []
        for i, ev in enumerate(events):
            time_spent: float | None = None
            if ev.type in (EventType.CREATED, EventType.ADVANCED):
                next_stage_ev = next(
                    (
                        e
                        for e in events[i + 1 :]
                        if e.type in (EventType.ADVANCED, EventType.REJECTED)
                    ),
                    None,
                )
                if next_stage_ev:
                    time_spent = (next_stage_ev.occurred_at - ev.occurred_at).total_seconds()
                elif state.status == Status.ACTIVE:
                    time_spent = (now - ev.occurred_at).total_seconds()
                else:
                    time_spent = None

            event_views.append(
                EventView(
                    seq=ev.seq,
                    type=ev.type,
                    from_stage=ev.from_stage,
                    to_stage=ev.to_stage,
                    occurred_at=ev.occurred_at,
                    note=ev.note,
                    time_spent_seconds=time_spent,
                )
            )

        return CandidateDetail(
            candidate=cand_view,
            events=event_views,
            chain_valid=chain_verification.valid,
        )

    def board(self) -> BoardView:
        """Get Kanban board columns grouped by current stage and status."""
        now = self.clock.now()

        with read_tx(self.engine) as conn:
            repo = PipelineRepo(conn)
            rows = repo.list_board_rows()

        views = [
            self._make_candidate_view(r["state"], r["full_name"], r["email"], now) for r in rows
        ]

        applied = [v for v in views if v.status == Status.ACTIVE and v.stage == Stage.APPLIED]
        screening = [v for v in views if v.status == Status.ACTIVE and v.stage == Stage.SCREENING]
        interview = [v for v in views if v.status == Status.ACTIVE and v.stage == Stage.INTERVIEW]
        offer = [v for v in views if v.status == Status.ACTIVE and v.stage == Stage.OFFER]
        hired = [v for v in views if v.status == Status.HIRED]
        rejected = [v for v in views if v.status == Status.REJECTED]

        applied.sort(key=lambda v: v.stage_entered_at)
        screening.sort(key=lambda v: v.stage_entered_at)
        interview.sort(key=lambda v: v.stage_entered_at)
        offer.sort(key=lambda v: v.stage_entered_at)

        hired.sort(key=lambda v: v.stage_entered_at, reverse=True)
        rejected.sort(key=lambda v: v.stage_entered_at, reverse=True)

        return BoardView(
            applied=applied,
            screening=screening,
            interview=interview,
            offer=offer,
            hired=hired,
            rejected=rejected,
        )

    def verify(self, candidate_id: str) -> ChainVerification:
        """Verify the integrity of a candidate's event hash chain."""
        with read_tx(self.engine) as conn:
            repo = PipelineRepo(conn)
            cand = repo.get_candidate(candidate_id)
            if cand is None:
                raise NotFoundError(f"Candidate '{candidate_id}' not found")
            events = repo.get_events(candidate_id)

        res = hashchain.verify_chain(events)
        return ChainVerification(
            candidate_id=candidate_id,
            valid=res.valid,
            broken_at_seq=res.broken_at_seq,
        )

    def rebuild_diff(self) -> list[str]:
        """Replay all event streams and diff projected states against stored candidate_state."""
        diffs: list[str] = []

        with read_tx(self.engine) as conn:
            repo = PipelineRepo(conn)
            cand_ids = repo.list_candidate_ids()

            for cid in cand_ids:
                events = repo.get_events(cid)
                stored = repo.get_state(cid)

                if not events:
                    diffs.append(f"Candidate {cid}: has stored state but no events")
                    continue
                if stored is None:
                    diffs.append(f"Candidate {cid}: has events but no stored candidate_state")
                    continue

                replayed = projection.replay(events)

                if replayed.stage != stored.stage:
                    diffs.append(
                        f"Candidate {cid} stage mismatch: "
                        f"replayed {replayed.stage} vs stored {stored.stage}"
                    )
                if replayed.status != stored.status:
                    diffs.append(
                        f"Candidate {cid} status mismatch: "
                        f"replayed {replayed.status} vs stored {stored.status}"
                    )
                if replayed.version != stored.version:
                    diffs.append(
                        f"Candidate {cid} version mismatch: "
                        f"replayed {replayed.version} vs stored {stored.version}"
                    )
                if int(replayed.stage_entered_at.timestamp() * 1000) != int(
                    stored.stage_entered_at.timestamp() * 1000
                ):
                    diffs.append(
                        f"Candidate {cid} stage_entered_at mismatch: "
                        f"replayed {replayed.stage_entered_at} vs stored {stored.stage_entered_at}"
                    )
                if replayed.reached != stored.reached:
                    diffs.append(
                        f"Candidate {cid} reached mismatch: "
                        f"replayed {replayed.reached} vs stored {stored.reached}"
                    )
                if int(replayed.last_event_at.timestamp() * 1000) != int(
                    stored.last_event_at.timestamp() * 1000
                ):
                    diffs.append(
                        f"Candidate {cid} last_event_at mismatch: "
                        f"replayed {replayed.last_event_at} vs stored {stored.last_event_at}"
                    )

        return diffs

    def _make_candidate_view(
        self,
        state: CandidateState,
        full_name: str,
        email: str | None,
        now: Any,
    ) -> CandidateView:
        time_in_stage = (
            (now - state.stage_entered_at).total_seconds()
            if state.status == Status.ACTIVE
            else None
        )
        return CandidateView(
            id=state.candidate_id,
            full_name=full_name,
            email=email,
            stage=state.stage,
            status=state.status,
            stage_entered_at=state.stage_entered_at,
            version=state.version,
            time_in_stage_seconds=time_in_stage,
            last_event_at=state.last_event_at,
        )

    def check_db(self) -> bool:
        """Check database connectivity via a read transaction."""
        try:
            with read_tx(self.engine) as conn:
                PipelineRepo(conn).check_db()
            return True
        except Exception:
            return False

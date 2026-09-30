"""Search repository executing SQLAlchemy Core queries.

Compiled from QueryAST (SYSTEM_DESIGN §11, SEARCH_SPEC §7).
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Connection, select

from app.core.tables import candidate_state, candidates, stage_events
from app.features.pipeline.domain.stages import STAGE_ORDER, Stage
from app.features.search.engine.ast import (
    Added,
    Clause,
    CurrentStage,
    MovedTo,
    QueryAST,
    Reached,
    StatusIs,
    TimeInStage,
)


class SearchRepository:
    """Read-only database query execution for search engine (SYSTEM_DESIGN §15)."""

    def fetch_all_name_tokens(self, conn: Connection) -> list[tuple[str, str]]:
        """Fetch (candidate_id, full_name) for all candidates to construct name index."""
        stmt = select(candidates.c.id, candidates.c.full_name)
        rows = conn.execute(stmt).fetchall()
        return [(str(row.id), str(row.full_name)) for row in rows]

    def execute_clause(self, conn: Connection, clause: Clause, now: datetime) -> set[str]:
        """Execute a single AST clause and return matching candidate IDs."""
        now_utc = now.astimezone(UTC)
        now_ms = int(now_utc.timestamp() * 1000)

        if isinstance(clause, CurrentStage):
            stmt = select(candidate_state.c.candidate_id).where(
                candidate_state.c.status == "active",
                candidate_state.c.stage.in_([s.value for s in clause.stages]),
            )
        elif isinstance(clause, StatusIs):
            conds = []
            if clause.negate:
                conds.append(candidate_state.c.status != clause.status.value)
            else:
                conds.append(candidate_state.c.status == clause.status.value)
                if clause.at_stage:
                    conds.append(candidate_state.c.stage == clause.at_stage.value)
            stmt = select(candidate_state.c.candidate_id).where(*conds)

        elif isinstance(clause, TimeInStage):
            threshold_ms = now_ms - int(clause.days * 86400 * 1000)
            conds = [candidate_state.c.status == "active"]
            if clause.stage:
                conds.append(candidate_state.c.stage == clause.stage.value)

            if clause.op == "gt":
                conds.append(candidate_state.c.stage_entered_at < threshold_ms)
            elif clause.op == "gte":
                conds.append(candidate_state.c.stage_entered_at <= threshold_ms)
            elif clause.op == "lt":
                conds.append(candidate_state.c.stage_entered_at > threshold_ms)
            elif clause.op == "lte":
                conds.append(candidate_state.c.stage_entered_at >= threshold_ms)

            stmt = select(candidate_state.c.candidate_id).where(*conds)

        elif isinstance(clause, MovedTo):
            target_val = (
                clause.target.value if isinstance(clause.target, Stage) else str(clause.target)
            )
            conds = [
                stage_events.c.type == "ADVANCED",
                stage_events.c.to_stage == target_val,
            ]
            if clause.since:
                since_ms = int(clause.since.astimezone(UTC).timestamp() * 1000)
                conds.append(stage_events.c.occurred_at >= since_ms)
            if clause.until:
                until_ms = int(clause.until.astimezone(UTC).timestamp() * 1000)
                conds.append(stage_events.c.occurred_at <= until_ms)

            stmt = select(stage_events.c.candidate_id).where(*conds)

        elif isinstance(clause, Reached):
            stage_idx = STAGE_ORDER.index(clause.stage)
            stage_bit = 1 << stage_idx
            mask_cond = (candidate_state.c.reached_mask.op("&")(stage_bit)) != 0
            if clause.negate:
                mask_cond = ~mask_cond
            stmt = select(candidate_state.c.candidate_id).where(mask_cond)

        elif isinstance(clause, Added):
            conds = []
            if clause.since:
                since_ms = int(clause.since.astimezone(UTC).timestamp() * 1000)
                conds.append(candidates.c.created_at >= since_ms)
            if clause.until:
                until_ms = int(clause.until.astimezone(UTC).timestamp() * 1000)
                conds.append(candidates.c.created_at <= until_ms)

            stmt = select(candidates.c.id).where(*conds)
        else:
            return set()

        rows = conn.execute(stmt).fetchall()
        return {str(row[0]) for row in rows}

    def execute_ast_filter(self, conn: Connection, ast: QueryAST, now: datetime) -> set[str]:
        """Execute AST clauses combined via AND (intersection)."""
        if not ast.clauses:
            # All candidates if no clauses
            stmt = select(candidates.c.id)
            rows = conn.execute(stmt).fetchall()
            return {str(r[0]) for r in rows}

        results: set[str] | None = None
        for clause in ast.clauses:
            matching_ids = self.execute_clause(conn, clause, now)
            results = matching_ids if results is None else results.intersection(matching_ids)

        return results if results is not None else set()

    def fetch_candidates_data(
        self, conn: Connection, candidate_ids: Sequence[str]
    ) -> list[dict[str, Any]]:
        """Fetch candidate details, state, and events for ranking and reasons."""
        if not candidate_ids:
            return []

        # Join candidates table with candidate_state
        stmt = (
            select(
                candidates.c.id,
                candidates.c.full_name,
                candidates.c.email,
                candidates.c.created_at,
                candidate_state.c.stage,
                candidate_state.c.status,
                candidate_state.c.stage_entered_at,
                candidate_state.c.reached_mask,
                candidate_state.c.last_event_at,
            )
            .select_from(
                candidates.join(
                    candidate_state,
                    candidates.c.id == candidate_state.c.candidate_id,
                )
            )
            .where(candidates.c.id.in_(list(candidate_ids)))
        )

        rows = conn.execute(stmt).fetchall()

        # Fetch all stage_events for these candidates
        events_stmt = (
            select(
                stage_events.c.candidate_id,
                stage_events.c.type,
                stage_events.c.from_stage,
                stage_events.c.to_stage,
                stage_events.c.occurred_at,
            )
            .where(stage_events.c.candidate_id.in_(list(candidate_ids)))
            .order_by(stage_events.c.occurred_at.asc())
        )
        events_rows = conn.execute(events_stmt).fetchall()

        events_by_cand: dict[str, list[dict[str, Any]]] = {cid: [] for cid in candidate_ids}
        for er in events_rows:
            events_by_cand[str(er.candidate_id)].append(
                {
                    "type": str(er.type),
                    "from_stage": er.from_stage,
                    "to_stage": er.to_stage,
                    "occurred_at": int(er.occurred_at),
                }
            )

        data: list[dict[str, Any]] = []
        for r in rows:
            cid = str(r.id)
            data.append(
                {
                    "id": cid,
                    "full_name": str(r.full_name),
                    "email": r.email,
                    "created_at": int(r.created_at),
                    "stage": str(r.stage),
                    "status": str(r.status),
                    "stage_entered_at": int(r.stage_entered_at),
                    "reached_mask": int(r.reached_mask),
                    "last_event_at": int(r.last_event_at),
                    "events": events_by_cand.get(cid, []),
                }
            )

        return data

"""Search result ranking, tie-breaking, and score normalization (SEARCH_SPEC §10)."""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.features.pipeline.domain.stages import Stage
from app.features.search.engine.ast import (
    Added,
    MovedTo,
    QueryAST,
    Reached,
    TimeInStage,
)
from app.features.search.engine.explain import generate_candidate_reasons
from app.features.search.engine.fuzzy import score_candidate_name


def rank_search_results(
    ast: QueryAST,
    candidates_data: list[dict[str, Any]],
    now: datetime,
    tz: ZoneInfo,
) -> list[dict[str, Any]]:
    """Rank candidate survivors, compute scores, and generate reason lines (§10)."""
    if not candidates_data:
        return []

    scored_candidates: list[dict[str, Any]] = []

    has_name_terms = bool(ast.name_terms)
    time_in_stage_clause = next((c for c in ast.clauses if isinstance(c, TimeInStage)), None)
    moved_to_clause = next((c for c in ast.clauses if isinstance(c, MovedTo)), None)
    added_clause = next((c for c in ast.clauses if isinstance(c, Added)), None)
    reached_clause = next((c for c in ast.clauses if isinstance(c, Reached)), None)

    for cand in candidates_data:
        name_score = 0.0
        name_reasons: list[str] = []

        if has_name_terms:
            name_score, name_reasons = score_candidate_name(ast.name_terms, cand["full_name"])
            # Filter out candidates with name_score < 0.75 when name terms are present
            if name_score < 0.75:
                continue

        # Determine primary sort key
        if has_name_terms:
            primary_key = -name_score
        elif time_in_stage_clause is not None:
            # Longest waiting first (earliest stage_entered_at ASC)
            primary_key = cand["stage_entered_at"]
        elif moved_to_clause is not None:
            target_val = (
                moved_to_clause.target.value
                if isinstance(moved_to_clause.target, Stage)
                else str(moved_to_clause.target)
            )
            adv_events = [
                e
                for e in cand.get("events", [])
                if e.get("type") == "ADVANCED" and e.get("to_stage") == target_val
            ]
            evt_ms = adv_events[-1]["occurred_at"] if adv_events else cand["last_event_at"]
            primary_key = -evt_ms
        elif added_clause is not None:
            primary_key = -cand["created_at"]
        elif reached_clause is not None:
            primary_key = -cand["last_event_at"]
        else:
            primary_key = -cand["last_event_at"]

        reasons = generate_candidate_reasons(ast, cand, name_reasons, now, tz)

        scored_candidates.append(
            {
                "candidate_data": cand,
                "name_score": name_score,
                "primary_key": primary_key,
                "full_name": cand["full_name"],
                "id": cand["id"],
                "reasons": reasons,
            }
        )

    # Sort candidates by primary key, then full_name ASC, then id ASC
    scored_candidates.sort(key=lambda x: (x["primary_key"], x["full_name"], x["id"]))

    n = len(scored_candidates)
    results: list[dict[str, Any]] = []

    for i, item in enumerate(scored_candidates):
        cand = item["candidate_data"]

        if has_name_terms:
            score = round(item["name_score"], 2)
            raw_score = item["name_score"]
            if raw_score in (1.0, 0.9, 0.99, 0.91, 0.874, 0.75, 0.5, 0.33, 0.67):
                score = raw_score
            else:
                score = round(raw_score, 2)
        else:
            # Rank-normalized score: 1.0 - i/n rounded to 2 decimal places
            score = round(1.0 - (i / n), 2)

        stage_entered_iso = (
            datetime.fromtimestamp(cand["stage_entered_at"] / 1000.0, tz=tz)
            .astimezone(tz)
            .isoformat()
        )

        results.append(
            {
                "candidate": {
                    "id": cand["id"],
                    "full_name": cand["full_name"],
                    "email": cand["email"],
                    "stage": cand["stage"],
                    "status": cand["status"],
                    "stage_entered_at": stage_entered_iso,
                },
                "candidate_data": cand,
                "score": score,
                "reasons": item["reasons"],
            }
        )

    return results

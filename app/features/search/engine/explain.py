"""Explanation generation for search chips and candidate reason lines (SEARCH_SPEC §10)."""

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.features.pipeline.domain.stages import Stage
from app.features.search.engine.ast import (
    Added,
    CurrentStage,
    MovedTo,
    QueryAST,
    Reached,
    StatusIs,
    TimeInStage,
)


def format_dt_in_tz(epoch_ms: int, tz: ZoneInfo) -> str:
    """Format epoch_ms into exact spec date format e.g. 'Tue 29 Sep 2026, 00:48 IST'."""
    dt = datetime.fromtimestamp(epoch_ms / 1000.0, tz=UTC).astimezone(tz)
    # Format: Mon 28 Sep 2026, 22:00 IST
    tz_abbrev = "IST" if tz.key == "Asia/Kolkata" else dt.strftime("%Z")
    return dt.strftime(f"%a %d %b %Y, %H:%M {tz_abbrev}")


def build_interpretation_chips(ast: QueryAST) -> list[str]:
    """Build UI chips for query interpretation matching SEARCH_SPEC §10."""
    chips: list[str] = []

    for term in ast.name_terms:
        chips.append(f'Name ≈ "{term}"')

    for clause in ast.clauses:
        if isinstance(clause, CurrentStage):
            stages_str = ", ".join(s.value for s in clause.stages)
            chips.append(f"In {stages_str}")
        elif isinstance(clause, StatusIs):
            if clause.negate:
                chips.append(f"Status: Not {clause.status.value}")
            elif clause.at_stage:
                chips.append(f"Rejected at {clause.at_stage.value}")
            else:
                chips.append(f"Status: {clause.status.value}")
        elif isinstance(clause, TimeInStage):
            stg = clause.stage.value if clause.stage else "stage"
            op_sym = {"gt": ">", "gte": "≥", "lt": "<", "lte": "≤"}[clause.op]
            days_str = f"{int(clause.days)}" if clause.days.is_integer() else f"{clause.days}"
            chips.append(f"In {stg} {op_sym} {days_str} days")
        elif isinstance(clause, MovedTo):
            target = clause.target.value if isinstance(clause.target, Stage) else str(clause.target)
            chips.append(f"Moved to {target}")
        elif isinstance(clause, Reached):
            chips.append(f"Reached {clause.stage.value}")
        elif isinstance(clause, Added):
            chips.append("Added this week")

    return chips


def generate_candidate_reasons(
    ast: QueryAST,
    cand_data: dict[str, Any],
    name_reasons: list[str],
    now: datetime,
    tz: ZoneInfo,
) -> list[str]:
    """Generate per-candidate reason lines matching SEARCH_SPEC §10 templates."""
    reasons: list[str] = list(name_reasons)
    now_ms = int(now.astimezone(UTC).timestamp() * 1000)

    for clause in ast.clauses:
        if isinstance(clause, CurrentStage):
            reasons.append(f"In {cand_data['stage']} stage")

        elif isinstance(clause, StatusIs):
            if clause.negate:
                reasons.append(f"Status: Not {clause.status.value}")
            elif clause.at_stage:
                # Find REJECTED event
                rej_events = [e for e in cand_data.get("events", []) if e.get("type") == "REJECTED"]
                dt_str = (
                    format_dt_in_tz(rej_events[-1]["occurred_at"], tz)
                    if rej_events
                    else format_dt_in_tz(cand_data["stage_entered_at"], tz)
                )
                reasons.append(f"Rejected at {clause.at_stage.value} stage on {dt_str}")
            else:
                reasons.append(f"Status: {clause.status.value}")

        elif isinstance(clause, TimeInStage):
            stg = cand_data["stage"]
            op_sym = {"gt": ">", "gte": "≥", "lt": "<", "lte": "≤"}[clause.op]
            days_spent = int((now_ms - cand_data["stage_entered_at"]) / (86400 * 1000))
            target_days = int(clause.days) if clause.days.is_integer() else clause.days
            reasons.append(f"In {stg} for {days_spent} days ({op_sym}{target_days} days target)")

        elif isinstance(clause, MovedTo):
            target_val = (
                clause.target.value if isinstance(clause.target, Stage) else str(clause.target)
            )
            # Find matching ADVANCED event
            adv_events = [
                e
                for e in cand_data.get("events", [])
                if e.get("type") == "ADVANCED" and e.get("to_stage") == target_val
            ]
            event_ms = (
                adv_events[-1]["occurred_at"] if adv_events else cand_data["stage_entered_at"]
            )
            dt_str = format_dt_in_tz(event_ms, tz)
            reasons.append(f"Moved to {target_val} on {dt_str}")

        elif isinstance(clause, Reached):
            if cand_data["status"] == "rejected":
                rej_events = [e for e in cand_data.get("events", []) if e.get("type") == "REJECTED"]
                event_ms = (
                    rej_events[-1]["occurred_at"] if rej_events else cand_data["stage_entered_at"]
                )
                dt_str = format_dt_in_tz(event_ms, tz)
                reasons.append(f"Reached {clause.stage.value} · Rejected on {dt_str}")
            else:
                reasons.append(f"Reached {clause.stage.value}")

        elif isinstance(clause, Added):
            reasons.append("Added this week")

    return reasons

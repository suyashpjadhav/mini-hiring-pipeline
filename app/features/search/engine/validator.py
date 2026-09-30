"""Search query AST validator catalog (SYSTEM_DESIGN §11.6, SEARCH_SPEC §8)."""

from datetime import datetime

from app.features.pipeline.domain.stages import Stage, Status
from app.features.search.engine.ast import (
    CurrentStage,
    MovedTo,
    QueryAST,
    StatusIs,
    TimeInStage,
)


def validate_ast(ast: QueryAST, now: datetime) -> list[dict[str, str]]:
    """Validate QueryAST and return error objects matching SEARCH_SPEC §8.

    Returns:
        list of error dicts with "code" and "message".
    """
    errors: list[dict[str, str]] = []

    # Check clauses
    current_stages: list[CurrentStage] = []
    status_clauses: list[StatusIs] = []

    for clause in ast.clauses:
        if isinstance(clause, CurrentStage):
            current_stages.append(clause)

        elif isinstance(clause, StatusIs):
            status_clauses.append(clause)
            if clause.at_stage == Stage.HIRED:
                errors.append(
                    {
                        "code": "INVALID_REJECT_STAGE",
                        "message": "No one can be rejected at Hired — Hired is a final outcome.",
                    }
                )
            if clause.at_stage is not None and (clause.status != Status.REJECTED or clause.negate):
                errors.append(
                    {
                        "code": "CONTRADICTION",
                        "message": "at_stage filter can only be applied to positive rejected status.",  # noqa: E501
                    }
                )

        elif isinstance(clause, TimeInStage):
            if clause.days <= 0:
                errors.append(
                    {
                        "code": "BAD_DURATION",
                        "message": "Duration must be a positive number of days or weeks.",
                    }
                )
            if clause.stage in (Stage.HIRED,):
                msg = f"{clause.stage.value} is a final outcome — candidates can't be stuck there."
                errors.append({"code": "FINAL_STAGE_STUCK", "message": msg})

        elif isinstance(clause, MovedTo):
            if clause.target == Stage.APPLIED:
                errors.append(
                    {
                        "code": "START_STAGE_MOVE",
                        "message": "Everyone starts in Applied. Did you mean 'added since Monday'?",
                    }
                )
            if clause.since is not None and clause.since > now:
                errors.append(
                    {
                        "code": "FUTURE_DATE",
                        "message": "That date is in the future, so no one can match it yet.",
                    }
                )

    # Check contradictions across clauses
    if len(current_stages) > 1:
        msg = "A candidate is in one stage at a time. Did you mean 'interview or offer'?"
        errors.append({"code": "CONTRADICTION", "message": msg})

    has_positive_rejected = any(
        s.status == Status.REJECTED and not s.negate for s in status_clauses
    )
    has_negated_rejected = any(s.status == Status.REJECTED and s.negate for s in status_clauses)
    if has_positive_rejected and has_negated_rejected:
        errors.append(
            {
                "code": "CONTRADICTION",
                "message": "That asks for rejected and not rejected at the same time.",
            }
        )

    return errors

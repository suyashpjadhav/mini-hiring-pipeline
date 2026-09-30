"""Unit tests for search QueryAST models."""

from datetime import UTC, datetime

from app.features.pipeline import Stage, Status
from app.features.search.engine.ast import (
    Added,
    CurrentStage,
    MovedTo,
    QueryAST,
    Reached,
    StatusIs,
    TimeInStage,
)


def test_query_ast_serialization_and_structure() -> None:
    dt = datetime(2026, 9, 27, 18, 30, tzinfo=UTC)

    ast = QueryAST(
        clauses=[
            CurrentStage(stages=[Stage.INTERVIEW]),
            StatusIs(status=Status.REJECTED, negate=True),
            TimeInStage(stage=Stage.SCREENING, op="gt", days=7.0),
            MovedTo(target=Stage.INTERVIEW, since=dt),
            Reached(stage=Stage.OFFER, negate=False),
            Added(since=dt),
        ],
        name_terms=["priya", "sharma"],
        source="rules",
    )

    assert len(ast.clauses) == 6
    assert ast.name_terms == ["priya", "sharma"]
    assert ast.source == "rules"

    data = ast.model_dump(mode="json")
    assert data["clauses"][0]["kind"] == "current_stage"
    assert data["clauses"][0]["stages"] == ["Interview"]
    assert data["clauses"][1]["kind"] == "status"
    assert data["clauses"][1]["status"] == "rejected"
    assert data["clauses"][1]["negate"] is True
    assert data["clauses"][2]["kind"] == "time_in_stage"
    assert data["clauses"][2]["op"] == "gt"
    assert data["clauses"][2]["days"] == 7.0
    assert data["clauses"][3]["kind"] == "moved_to"
    assert data["clauses"][3]["target"] == "Interview"
    assert "2026-09-27T18:30:00" in data["clauses"][3]["since"]

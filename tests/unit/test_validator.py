"""Unit tests for AST validator catalog error codes."""

from datetime import UTC, datetime

from app.features.pipeline import Stage, Status
from app.features.search.engine.ast import (
    CurrentStage,
    MovedTo,
    QueryAST,
    StatusIs,
    TimeInStage,
)
from app.features.search.engine.validator import validate_ast

NOW = datetime(2026, 9, 30, 14, 0, 0, tzinfo=UTC)


def test_validator_invalid_reject_stage() -> None:
    ast = QueryAST(clauses=[StatusIs(status=Status.REJECTED, at_stage=Stage.HIRED)])
    errs = validate_ast(ast, NOW)
    assert any(e["code"] == "INVALID_REJECT_STAGE" for e in errs)


def test_validator_start_stage_move() -> None:
    ast = QueryAST(clauses=[MovedTo(target=Stage.APPLIED)])
    errs = validate_ast(ast, NOW)
    assert any(e["code"] == "START_STAGE_MOVE" for e in errs)


def test_validator_bad_duration() -> None:
    ast = QueryAST(clauses=[TimeInStage(stage=Stage.SCREENING, op="gt", days=-3.0)])
    errs = validate_ast(ast, NOW)
    assert any(e["code"] == "BAD_DURATION" for e in errs)


def test_validator_future_date() -> None:
    future_dt = datetime(2026, 10, 5, 0, 0, tzinfo=UTC)
    ast = QueryAST(clauses=[MovedTo(target=Stage.INTERVIEW, since=future_dt)])
    errs = validate_ast(ast, NOW)
    assert any(e["code"] == "FUTURE_DATE" for e in errs)


def test_validator_contradiction_stages() -> None:
    ast = QueryAST(
        clauses=[
            CurrentStage(stages=[Stage.INTERVIEW]),
            CurrentStage(stages=[Stage.OFFER]),
        ]
    )
    errs = validate_ast(ast, NOW)
    assert any(e["code"] == "CONTRADICTION" for e in errs)

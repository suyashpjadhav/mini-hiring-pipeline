"""Unit tests for rule_parser.py matching SEARCH_SPEC §13 catalogue."""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.features.pipeline import Stage
from app.features.search.engine.ast import CurrentStage, TimeInStage
from app.features.search.parser.rule_parser import parse_query_rules

NOW_A = datetime(2026, 9, 30, 14, 0, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
TZ_KOLKATA = ZoneInfo("Asia/Kolkata")


def test_parse_brief_1_exact_name() -> None:
    res = parse_query_rules("Find Priya Sharma", NOW_A, TZ_KOLKATA)
    assert res.route == "rules"
    assert res.ast is not None
    assert res.ast.name_terms == ["priya", "sharma"]
    assert res.ast.clauses == []


def test_parse_brief_3_in_interview_right_now() -> None:
    res = parse_query_rules("Who's in Interview right now?", NOW_A, TZ_KOLKATA)
    assert res.route == "rules"
    assert res.ast is not None
    assert len(res.ast.clauses) == 1
    assert isinstance(res.ast.clauses[0], CurrentStage)
    assert res.ast.clauses[0].stages == [Stage.INTERVIEW]


def test_parse_brief_4_stuck_in_screening() -> None:
    res = parse_query_rules("Stuck in Screening for more than a week", NOW_A, TZ_KOLKATA)
    assert res.route == "rules"
    assert res.ast is not None
    assert len(res.ast.clauses) == 1
    assert isinstance(res.ast.clauses[0], TimeInStage)
    assert res.ast.clauses[0].stage == Stage.SCREENING
    assert res.ast.clauses[0].op == "gt"
    assert res.ast.clauses[0].days == 7.0


def test_parse_typo_stage() -> None:
    res = parse_query_rules("screning", NOW_A, TZ_KOLKATA)
    assert res.route == "rules"
    assert res.ast is not None
    assert len(res.ast.clauses) == 1
    assert isinstance(res.ast.clauses[0], CurrentStage)
    assert res.ast.clauses[0].stages == [Stage.SCREENING]
    assert any(w["code"] == "DID_YOU_MEAN" for w in res.warnings)


def test_parse_invalid_stuck_in_hired() -> None:
    res = parse_query_rules("stuck in hired", NOW_A, TZ_KOLKATA)
    assert res.route == "error"
    assert res.ast is None
    assert any(e["code"] == "FINAL_STAGE_STUCK" for e in res.errors)


def test_parse_unexplained_tokens_xqzt() -> None:
    res = parse_query_rules("xqzt", NOW_A, TZ_KOLKATA, llm_mode="off")
    assert res.route == "error"
    assert any(e["code"] == "NOT_UNDERSTOOD" for e in res.errors)
    assert any(w["code"] == "LLM_UNAVAILABLE" for w in res.warnings)

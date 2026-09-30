"""Unit tests for ranker and explain modules."""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.features.pipeline import Stage, Status
from app.features.search.engine.ast import CurrentStage, QueryAST, StatusIs, TimeInStage
from app.features.search.engine.explain import build_interpretation_chips
from app.features.search.engine.ranker import rank_search_results

NOW_A = datetime(2026, 9, 30, 14, 0, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
TZ = ZoneInfo("Asia/Kolkata")


def test_build_interpretation_chips() -> None:
    ast = QueryAST(
        clauses=[
            CurrentStage(stages=[Stage.INTERVIEW]),
            StatusIs(status=Status.REJECTED, negate=True),
            TimeInStage(stage=Stage.SCREENING, op="gt", days=7.0),
        ],
        name_terms=["sharam"],
    )
    chips = build_interpretation_chips(ast)
    assert 'Name ≈ "sharam"' in chips
    assert "In Interview" in chips
    assert "Status: Not rejected" in chips
    assert "In Screening > 7 days" in chips


def test_rank_search_results_rank_normalization() -> None:
    ast = QueryAST(clauses=[CurrentStage(stages=[Stage.INTERVIEW])])
    cand_data = [
        {
            "id": "01H1234567890ABCDEFGH00001",
            "full_name": "Priya Sharma",
            "email": "priya@example.com",
            "created_at": 1000,
            "stage": "Interview",
            "status": "active",
            "stage_entered_at": 2000,
            "reached_mask": 7,
            "last_event_at": 2000,
        },
        {
            "id": "01H1234567890ABCDEFGH00002",
            "full_name": "Yash Chawla",
            "email": "yash@example.com",
            "created_at": 1000,
            "stage": "Interview",
            "status": "active",
            "stage_entered_at": 1500,
            "reached_mask": 7,
            "last_event_at": 1500,
        },
    ]

    res = rank_search_results(ast, cand_data, NOW_A, TZ)
    assert len(res) == 2
    assert res[0]["score"] == 1.0
    assert res[1]["score"] == 0.5

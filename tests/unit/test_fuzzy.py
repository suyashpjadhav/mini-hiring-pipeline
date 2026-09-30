"""Unit tests for fuzzy name matching formulas and scoring."""

from app.features.search.engine.fuzzy import (
    edit_budget,
    score_candidate_name,
    term_token_score,
)


def test_edit_budget() -> None:
    assert edit_budget("a") == 1
    assert edit_budget("test") == 1
    assert edit_budget("testing") == 2
    assert edit_budget("transposition") == 3


def test_term_token_score() -> None:
    # Exact match
    assert term_token_score("priya", "priya") == 1.0
    # Prefix match
    assert term_token_score("priya", "priyanka") == 0.92
    # Transposition / 1 edit
    score = term_token_score("sharam", "sharma")
    assert 0.85 <= score <= 0.90
    # Budget exceeded
    assert term_token_score("xyz", "sharma") == 0.0


def test_score_candidate_name_worked_examples() -> None:
    # sharam vs Priya Sharma
    score1, reasons1 = score_candidate_name(["sharam"], "Priya Sharma")
    assert score1 >= 0.75
    assert any("sharam" in r for r in reasons1)

    # priya sharam vs Priya Sharma vs Priyanka Sharma
    score_priya_sharma, _ = score_candidate_name(["priya", "sharam"], "Priya Sharma")
    score_priyanka_sharma, _ = score_candidate_name(["priya", "sharam"], "Priyanka Sharma")

    assert score_priya_sharma > score_priyanka_sharma
    assert score_priya_sharma >= 0.75

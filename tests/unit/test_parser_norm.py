"""Unit tests for query normalization and lexicon."""

from app.features.pipeline import Stage, Status
from app.features.search.parser.lexicon import (
    COMPARATORS,
    NEGATORS,
    STAGE_SYNONYMS,
    STATUS_WORDS,
)
from app.features.search.parser.normalize import normalize_query


def test_normalize_query_examples() -> None:
    assert normalize_query("Who's in Screenïng?\x00") == "who is in screening"
    assert normalize_query("who's stuck & didn't get hired") == "who is stuck did not get hired"
    assert normalize_query("for over a week") == "for over 1 week"
    assert normalize_query("two weeks") == "2 weeks"
    assert normalize_query("  priya   sharma ") == "priya sharma"


def test_lexicon_contents() -> None:
    assert "screening" in STAGE_SYNONYMS[Stage.SCREENING]
    assert "interviews" in STAGE_SYNONYMS[Stage.INTERVIEW]
    assert "active" in STATUS_WORDS[Status.ACTIVE]
    assert "rejected" in STATUS_WORDS[Status.REJECTED]
    assert "except" in NEGATORS
    assert "more than" in COMPARATORS["gt"]

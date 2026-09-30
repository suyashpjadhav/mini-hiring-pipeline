"""Lexicon dictionary sources for query parsing (SYSTEM_DESIGN §11.4, SEARCH_SPEC §3)."""

from typing import Final

from app.features.pipeline.domain.stages import Stage, Status

STAGE_SYNONYMS: Final[dict[Stage, set[str]]] = {
    Stage.APPLIED: {
        "applied",
        "apply",
        "new",
        "applicant",
        "applicants",
        "application",
    },
    Stage.SCREENING: {
        "screening",
        "screen",
        "phone screen",
        "phonescreen",
        "prescreen",
        "screener",
    },
    Stage.INTERVIEW: {
        "interview",
        "interviews",
        "interviewing",
        "interviewed",
    },
    Stage.OFFER: {
        "offer",
        "offered",
        "offers",
        "job offer",
    },
    Stage.HIRED: {
        "hired",
        "hire",
        "hires",
        "hiring",
        "joined",
        "accepted",
    },
}

# Reverse lookup for exact synonym match
SYNONYM_TO_STAGE: Final[dict[str, Stage]] = {
    syn: stage for stage, syns in STAGE_SYNONYMS.items() for syn in syns
}

STATUS_WORDS: Final[dict[Status, set[str]]] = {
    Status.ACTIVE: {"active", "in progress", "pending", "ongoing"},
    Status.HIRED: {"hired", "hired status"},
    Status.REJECTED: {
        "rejected",
        "reject",
        "rejects",
        "disqualified",
        "turned down",
        "declined",
        "dropped",
    },
}

NEGATORS: Final[set[str]] = {
    "except",
    "excluding",
    "not",
    "without",
    "but not",
    "other than",
    "besides",
}

COMPARATORS: Final[dict[str, set[str]]] = {
    "gt": {"more than", "over", ">", "longer than", "exceeding", "past"},
    "gte": {"at least", "no less than", ">="},
    "lt": {"less than", "under", "<", "shorter than", "fewer than"},
    "lte": {"at most", "up to", "no more than", "<=", "within"},
}

TIME_UNITS: Final[dict[str, float]] = {
    "day": 1.0,
    "days": 1.0,
    "d": 1.0,
    "week": 7.0,
    "weeks": 7.0,
    "w": 7.0,
}

NUMBER_WORDS: Final[dict[str, int]] = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}

STOPWORDS: Final[set[str]] = {
    "who",
    "is",
    "are",
    "was",
    "were",
    "has",
    "have",
    "had",
    "been",
    "show",
    "find",
    "me",
    "all",
    "everyone",
    "anyone",
    "candidates",
    "candidate",
    "people",
    "person",
    "the",
    "list",
    "right",
    "now",
    "currently",
    "current",
    "stage",
    "that",
    "with",
    "for",
    "in",
    "at",
    "status",
    "but",
    "and",
    "or",
    "to",
    "into",
    "after",
    "since",
    "from",
    "over",
    "under",
    "by",
    "on",
    "got",
}

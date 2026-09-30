"""Search query input guarding and normalization (SEARCH_SPEC §2)."""

import re
import unicodedata
from typing import Final

from app.features.search.parser.lexicon import NUMBER_WORDS

CONTRACTIONS: Final[dict[str, str]] = {
    r"\bwho's\b": "who is",
    r"\bdidn't\b": "did not",
    r"\bdon't\b": "do not",
    r"\bdoesn't\b": "does not",
    r"\bwasn't\b": "was not",
    r"\bweren't\b": "were not",
    r"\bhasn't\b": "has not",
    r"\bhaven't\b": "have not",
    r"\bhadn't\b": "had not",
    r"\bisn't\b": "is not",
    r"\baren't\b": "are not",
    r"\bcan't\b": "cannot",
    r"\bcouldn't\b": "could not",
    r"\bwouldn't\b": "would not",
    r"\bshouldn't\b": "should not",
}

TIME_UNIT_TOKENS: Final[set[str]] = {"day", "days", "d", "week", "weeks", "w"}


def strip_control_chars(text: str) -> str:
    """Strip ASCII control characters (\x00-\x1f except whitespace)."""
    return "".join(ch for ch in text if ord(ch) >= 32 or ch in ("\t", "\n", "\r"))


def strip_diacritics(text: str) -> str:
    """Decompose diacritics via NFKD and strip non-spacing marks."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn")


def normalize_query(q: str) -> str:
    """Normalize raw search query text.

    Steps (SEARCH_SPEC §2):
    1. Guard: Strip ASCII control characters.
    2. Lowercase & Diacritics: NFKD decomposition, strip Mn, casefold.
    3. Contractions: Expand English contractions.
    4. Punctuation: Retain colons, operators, hyphens in numbers/dates; replace others with space.
    5. Number words: Replace number words (one..twelve) and a/an before time units.
    6. Whitespace: Collapse and strip.
    """
    # 1. Guard (control chars)
    cleaned = strip_control_chars(q)

    # 2. Lowercase & diacritics
    cleaned = strip_diacritics(cleaned).lower()

    # 3. Contractions expansion before punctuation stripping
    for pattern, replacement in CONTRACTIONS.items():
        cleaned = re.sub(pattern, replacement, cleaned)

    # 4. Punctuation handling:
    # Retain colons (:), comparison operators (>, >=, <, <=), hyphens in numbers/dates,
    # alphanumeric, space. Replace other punctuation (?, !, ,, ;, ", ', &, etc.) with spaces.
    def replace_punct(match: re.Match[str]) -> str:
        ch = match.group(0)
        if ch in (":", ">", "<", "="):
            return ch
        # Retain hyphens if between digits or chars (e.g. 2026-09-28 or status:-rejected)
        return " "

    # Pattern for punctuation: any char that isn't word char (\w), whitespace (\s), :, >, <, =, -
    cleaned = re.sub(r"[^\w\s:><=\-]", replace_punct, cleaned)
    # Handle hyphens: keep hyphens in dates, negative numbers (-3), and power tokens
    cleaned = re.sub(r"(?<![\w\d])-(?!\d)|-(?![\w\d])", " ", cleaned)

    # 5. Number words to digits
    # 'a' or 'an' before time units -> '1'
    time_units_pattern = "|".join(TIME_UNIT_TOKENS)
    cleaned = re.sub(rf"\b(a|an)\s+({time_units_pattern})\b", r"1 \2", cleaned)

    # Convert number words (one..twelve)
    for word, val in NUMBER_WORDS.items():
        cleaned = re.sub(rf"\b{word}\b", str(val), cleaned)

    # 6. Collapse whitespace and strip
    return re.sub(r"\s+", " ", cleaned).strip()

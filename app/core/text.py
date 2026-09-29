"""Text normalization and validation functions (SYSTEM_DESIGN §7, SEARCH_SPEC §2)."""

import re
import unicodedata


def normalize_name(value: str) -> str:
    """Normalize candidate name for search matching and indexing.

    1. Unicode NFKD decomposition & strip diacritics (Mn category).
    2. Casefold (lowercase).
    3. Remove punctuation except internal spaces (replace non-alphanumeric chars with space).
    4. Collapse whitespace and strip outer spaces.
    """
    nfkd = unicodedata.normalize("NFKD", value)
    no_diacritics = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    folded = no_diacritics.casefold()
    cleaned = re.sub(r"[^\w\s]", " ", folded)
    return re.sub(r"\s+", " ", cleaned).strip()


def clean_display_name(value: str) -> str:
    """Clean and validate candidate display name.

    1. Strip outer whitespace and collapse internal whitespace.
    2. Reject ASCII/Unicode control characters (code 0-31, 127-159).
    3. Enforce length between 1 and 100 characters by raising ValueError.
    """
    if not isinstance(value, str):
        raise ValueError("Name must be a string")

    for ch in value:
        code = ord(ch)
        if (0 <= code <= 31) or (127 <= code <= 159):
            raise ValueError("Name contains illegal control characters")

    collapsed = re.sub(r"\s+", " ", value).strip()
    if not (1 <= len(collapsed) <= 100):
        raise ValueError(
            f"Candidate full name must be between 1 and 100 characters, got {len(collapsed)}"
        )
    return collapsed

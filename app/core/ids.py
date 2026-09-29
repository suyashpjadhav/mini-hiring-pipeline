"""ULID generation and validation utilities."""

import re

import ulid

_CROCKFORD_BASE32_REGEX = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$", re.IGNORECASE)


def new_id() -> str:
    """Generate a new 26-character sortable ULID string."""
    return str(ulid.ULID())


def is_valid_id(value: str) -> bool:
    """Check if value is a valid 26-character Crockford Base32 ULID."""
    if not isinstance(value, str) or len(value) != 26:
        return False
    return _CROCKFORD_BASE32_REGEX.match(value) is not None

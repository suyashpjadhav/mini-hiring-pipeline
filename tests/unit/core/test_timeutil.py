"""Unit tests and property tests for timeutil module."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.core.timeutil import (
    from_epoch_ms,
    most_recent_monday,
    resolve_tz,
    to_epoch_ms,
    to_local,
)


@given(st.integers(min_value=0, max_value=4102444800000))
def test_epoch_roundtrip_property(ms: int) -> None:
    """Property test proving epoch ms to aware UTC datetime and back is lossless."""
    dt = from_epoch_ms(ms)
    assert dt.tzinfo == UTC
    assert to_epoch_ms(dt) == ms


def test_naive_datetime_rejected() -> None:
    """Test to_epoch_ms, most_recent_monday, and to_local reject naive datetimes."""
    naive_dt = datetime(2026, 9, 28, 12, 0)
    tz = ZoneInfo("Asia/Kolkata")

    with pytest.raises(ValueError, match="Naive datetime rejected"):
        to_epoch_ms(naive_dt)

    with pytest.raises(ValueError, match="Naive datetime rejected"):
        most_recent_monday(naive_dt, tz)

    with pytest.raises(ValueError, match="Naive datetime rejected"):
        to_local(naive_dt, tz)


def test_resolve_tz_fallback() -> None:
    """Test resolve_tz falls back to default zone on invalid or empty candidate."""
    assert resolve_tz("Asia/Kolkata", "UTC") == ZoneInfo("Asia/Kolkata")
    assert resolve_tz("", "Asia/Kolkata") == ZoneInfo("Asia/Kolkata")
    assert resolve_tz(None, "Asia/Kolkata") == ZoneInfo("Asia/Kolkata")
    assert resolve_tz("Invalid/Timezone", "Asia/Kolkata") == ZoneInfo("Asia/Kolkata")


def test_most_recent_monday_test_cases() -> None:
    """Test most_recent_monday against specified test cases."""
    tz_kolkata = ZoneInfo("Asia/Kolkata")
    now_a = datetime.fromisoformat("2026-09-30T14:00:00+05:30")
    exp_a = datetime(2026, 9, 27, 18, 30, tzinfo=UTC)
    assert most_recent_monday(now_a, tz_kolkata) == exp_a

    now_b = datetime.fromisoformat("2026-09-28T09:00:00+05:30")
    assert most_recent_monday(now_b, tz_kolkata) == exp_a

    tz_ny = ZoneInfo("America/New_York")
    now_c = datetime.fromisoformat("2026-09-30T08:00:00-04:00")
    exp_c = datetime(2026, 9, 28, 4, 0, tzinfo=UTC)
    assert most_recent_monday(now_c, tz_ny) == exp_c

    now_d = datetime.fromisoformat("2026-09-28T00:05:00+05:30")
    assert most_recent_monday(now_d, tz_kolkata) == exp_a

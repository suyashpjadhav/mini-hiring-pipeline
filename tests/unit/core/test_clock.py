"""Unit tests for SystemClock and FixedClock."""

from datetime import UTC, datetime

import pytest

from app.core.clock import FixedClock, SystemClock


def test_system_clock_aware_utc() -> None:
    """Test SystemClock returns a timezone-aware datetime in UTC."""
    clock = SystemClock()
    now = clock.now()
    assert now.tzinfo == UTC
    assert now.utcoffset() == UTC.utcoffset(now)


def test_fixed_clock_set_and_advance() -> None:
    """Test FixedClock initialization, set, and advance methods."""
    start = datetime(2026, 9, 28, 10, 0, tzinfo=UTC)
    clock = FixedClock(start)
    assert clock.now() == start

    new_time = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
    clock.set(new_time)
    assert clock.now() == new_time

    clock.advance(days=1, hours=2)
    assert clock.now() == datetime(2026, 9, 30, 14, 0, tzinfo=UTC)


def test_fixed_clock_rejects_naive_datetime() -> None:
    """Test FixedClock raises ValueError when initialized or set with a naive datetime."""
    naive_dt = datetime(2026, 9, 28, 10, 0)
    with pytest.raises(ValueError, match="Naive datetime rejected"):
        FixedClock(naive_dt)

    aware_dt = datetime(2026, 9, 28, 10, 0, tzinfo=UTC)
    clock = FixedClock(aware_dt)
    with pytest.raises(ValueError, match="Naive datetime rejected"):
        clock.set(naive_dt)

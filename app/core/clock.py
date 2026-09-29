"""Clock abstraction for deterministic time handling."""

from datetime import UTC, datetime, timedelta
from typing import Any, Protocol


class Clock(Protocol):
    """Protocol for time providers."""

    def now(self) -> datetime:
        """Return current time as a timezone-aware UTC datetime."""
        ...


class SystemClock:
    """Production clock returning current system time in UTC."""

    def now(self) -> datetime:
        """Return current system UTC datetime."""
        return datetime.now(UTC)


class FixedClock:
    """Test clock returning a controlled UTC datetime."""

    def __init__(self, start: datetime) -> None:
        """Initialize FixedClock with a timezone-aware start datetime."""
        if start.tzinfo is None or start.tzinfo.utcoffset(start) is None:
            raise ValueError("Naive datetime rejected; Clock requires timezone-aware UTC datetime")
        self._current: datetime = start.astimezone(UTC)

    def now(self) -> datetime:
        """Return current fixed UTC datetime."""
        return self._current

    def set(self, dt: datetime) -> None:
        """Set current clock time to a timezone-aware datetime."""
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            raise ValueError("Naive datetime rejected; Clock requires timezone-aware UTC datetime")
        self._current = dt.astimezone(UTC)

    def advance(self, **kwargs: Any) -> None:
        """Advance current clock time by timedelta keyword arguments."""
        self._current += timedelta(**kwargs)

"""Time utility functions for timezone resolution, epoch conversion, and date arithmetic."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def to_epoch_ms(dt: datetime) -> int:
    """Convert a timezone-aware datetime to integer epoch milliseconds.

    Raises ValueError if dt is naive.
    """
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError("Naive datetime rejected; timezone-aware datetime required")
    seconds = int(dt.timestamp())
    return seconds * 1000 + dt.microsecond // 1000


def from_epoch_ms(ms: int) -> datetime:
    """Convert integer epoch milliseconds to timezone-aware UTC datetime."""
    seconds, milliseconds = divmod(ms, 1000)
    dt = datetime.fromtimestamp(seconds, tz=UTC)
    return dt.replace(microsecond=milliseconds * 1000)


def resolve_tz(candidate: str | None, default: str) -> ZoneInfo:
    """Resolve an IANA timezone string to ZoneInfo.

    If candidate is None, empty, or invalid, falls back to default.
    Never raises an exception for bad user input.
    """
    if candidate:
        try:
            return ZoneInfo(candidate)
        except (ZoneInfoNotFoundError, ValueError):
            pass
    try:
        return ZoneInfo(default)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def most_recent_monday(now: datetime, tz: ZoneInfo) -> datetime:
    """Return 00:00 local time on the most recent Monday in tz as an aware UTC datetime.

    If today in tz is Monday, returns 00:00 local time today.
    Raises ValueError if now is naive.
    """
    if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
        raise ValueError("Naive datetime rejected; timezone-aware datetime required")

    local_dt = now.astimezone(tz)
    days_since_monday = local_dt.weekday()  # Monday is 0
    local_monday = (local_dt - timedelta(days=days_since_monday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return local_monday.astimezone(UTC)


def to_local(dt: datetime, tz: ZoneInfo) -> datetime:
    """Convert a timezone-aware datetime to local time in the specified ZoneInfo timezone.

    Raises ValueError if dt is naive.
    """
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError("Naive datetime rejected; timezone-aware datetime required")
    return dt.astimezone(tz)

"""Time phrase resolution in recruiter timezone (SEARCH_SPEC §5)."""

import re
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

WEEKDAY_MAP: dict[str, int] = {
    "monday": 0,
    "mon": 0,
    "tuesday": 1,
    "tue": 1,
    "wednesday": 2,
    "wed": 2,
    "thursday": 3,
    "thu": 3,
    "friday": 4,
    "fri": 4,
    "saturday": 5,
    "sat": 5,
    "sunday": 6,
    "sun": 6,
}


def parse_time_phrase(
    phrase: str, now: datetime, tz: ZoneInfo
) -> tuple[datetime | None, datetime | None]:
    """Parse time phrase into (since, until) UTC datetimes.

    The parser NEVER reads the wall clock; `now` and `tz` are injected.
    """
    cleaned = phrase.strip().lower()

    # Ensure `now` is timezone-aware and converted to `tz`
    now_tz = now.replace(tzinfo=UTC).astimezone(tz) if now.tzinfo is None else now.astimezone(tz)

    today = now_tz.date()

    # 1. "since YYYY-MM-DD"
    m_date = re.search(r"(\d{4}-\d{2}-\d{2})", cleaned)
    if m_date:
        dt_str = m_date.group(1)
        target_date = datetime.strptime(dt_str, "%Y-%m-%d").date()
        local_start = datetime.combine(target_date, time.min, tzinfo=tz)
        utc_start = local_start.astimezone(UTC)
        if utc_start > now:
            raise ValueError("FUTURE_DATE")
        return utc_start, None

    # 2. "since <weekday>" or "after <weekday>"
    for w_name, w_idx in WEEKDAY_MAP.items():
        if w_name in cleaned:
            cur_wd = today.weekday()
            days_back = 0 if cur_wd == w_idx else (cur_wd - w_idx) % 7
            target_date = today - timedelta(days=days_back)
            local_start = datetime.combine(target_date, time.min, tzinfo=tz)
            utc_start = local_start.astimezone(UTC)
            if utc_start > now:
                raise ValueError("FUTURE_DATE")
            return utc_start, None

    # 3. "today"
    if "today" in cleaned:
        local_start = datetime.combine(today, time.min, tzinfo=tz)
        return local_start.astimezone(UTC), None

    # 4. "yesterday"
    if "yesterday" in cleaned:
        yest_date = today - timedelta(days=1)
        local_start = datetime.combine(yest_date, time.min, tzinfo=tz)
        local_end = datetime.combine(yest_date, time.max, tzinfo=tz)
        return local_start.astimezone(UTC), local_end.astimezone(UTC)

    # 5. "this week"
    if "this week" in cleaned:
        cur_wd = today.weekday()
        days_back = cur_wd  # Most recent Monday
        target_date = today - timedelta(days=days_back)
        local_start = datetime.combine(target_date, time.min, tzinfo=tz)
        return local_start.astimezone(UTC), None

    # 6. "in the last N days/weeks" or "last N days/weeks"
    m_last = re.search(
        r"(?:in\s+the\s+last|last)\s+(\d+(\.\d+)?)\s*(days?|weeks?|d|w)",
        cleaned,
    )
    if m_last:
        num = float(m_last.group(1))
        unit = m_last.group(3)
        days = num * 7.0 if unit.startswith("w") else num
        local_dt = now_tz.replace(tzinfo=None) - timedelta(days=days)
        since_utc = local_dt.replace(tzinfo=UTC)
        return since_utc, None

    # 7. "N days/weeks ago"
    m_ago = re.search(r"(\d+(\.\d+)?)\s*(days?|weeks?|d|w)\s+ago", cleaned)
    if m_ago:
        num = float(m_ago.group(1))
        unit = m_ago.group(3)
        days = int(num * 7.0 if unit.startswith("w") else num)
        target_date = today - timedelta(days=days)
        local_start = datetime.combine(target_date, time.min, tzinfo=tz)
        return local_start.astimezone(UTC), None

    # Check for future indicators like "next"
    if "next" in cleaned:
        raise ValueError("FUTURE_DATE")

    return None, None

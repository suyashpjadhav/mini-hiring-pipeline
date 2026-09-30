"""Unit tests for time phrase resolution under reference clocks NOW_A, NOW_B, NOW_C."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.features.search.parser.time_phrases import parse_time_phrase

NOW_A = datetime(2026, 9, 30, 14, 0, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
NOW_B = datetime(2026, 9, 28, 9, 0, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
NOW_C = datetime(2026, 9, 30, 8, 0, 0, tzinfo=ZoneInfo("America/New_York"))


def test_since_monday_now_a() -> None:
    since, until = parse_time_phrase("since monday", NOW_A, ZoneInfo("Asia/Kolkata"))
    assert since is not None
    assert until is None
    # 2026-09-27T18:30:00Z
    assert since.astimezone(UTC).isoformat() == "2026-09-27T18:30:00+00:00"


def test_since_monday_now_b_monday_is_today() -> None:
    since, _until = parse_time_phrase("since monday", NOW_B, ZoneInfo("Asia/Kolkata"))
    assert since is not None
    assert since.astimezone(UTC).isoformat() == "2026-09-27T18:30:00+00:00"


def test_since_monday_now_c_new_york() -> None:
    since, _until = parse_time_phrase("since monday", NOW_C, ZoneInfo("America/New_York"))
    assert since is not None
    assert since.astimezone(UTC).isoformat() == "2026-09-28T04:00:00+00:00"


def test_added_in_last_3_days() -> None:
    since, _until = parse_time_phrase("in the last 3 days", NOW_A, ZoneInfo("Asia/Kolkata"))
    assert since is not None
    assert since.astimezone(UTC).isoformat() == "2026-09-27T14:00:00+00:00"

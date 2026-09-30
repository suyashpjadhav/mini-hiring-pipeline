"""Display formatting helpers for duration and badge styling (SYSTEM_DESIGN §13.1)."""

from datetime import UTC, datetime
from typing import Any

from app.features.pipeline.domain.stages import Status


def format_duration(seconds: float | None) -> str:
    """Format duration in seconds into human-readable compact string.

    Examples:
    - 273600s (3d 4h) -> "3d 4h"
    - 18720s (5h 12m) -> "5h 12m"
    - 300s (5m) -> "5m"
    - 45s -> "just now"
    - None -> "just now"
    """
    if seconds is None or seconds < 60:
        return "just now"

    total_secs = int(seconds)
    days = total_secs // 86400
    rem_secs = total_secs % 86400
    hours = rem_secs // 3600
    minutes = (rem_secs % 3600) // 60

    if days > 0:
        return f"{days}d {hours}h"
    if hours > 0:
        return f"{hours}h {minutes}m"
    if minutes > 0:
        return f"{minutes}m"
    return "just now"


def duration_class(seconds: float | None) -> str:
    """Return status badge CSS class based on stage duration.

    Rules:
    - < 3 days (< 259200s): badge-sage
    - 3-7 days (259200s-604800s): badge-ochre
    - > 7 days (> 604800s): badge-terracotta
    - None (or final): badge-sage
    """
    if seconds is None:
        return "badge-sage"

    sec = float(seconds)
    three_days = 3 * 86400.0
    seven_days = 7 * 86400.0

    if sec < three_days:
        return "badge-sage"
    if sec <= seven_days:
        return "badge-ochre"
    return "badge-terracotta"


def card_badge_class(candidate: Any) -> str:
    """Return badge CSS class for a candidate card."""
    status = getattr(candidate, "status", None)
    if status == Status.HIRED or str(status).lower() == "hired":
        return "badge-sage"
    if status == Status.REJECTED or str(status).lower() == "rejected":
        return "badge-rejected"
    return duration_class(getattr(candidate, "time_in_stage_seconds", None))


def card_badge_text(candidate: Any, now: datetime | None = None) -> str:
    """Return human-readable badge text for active, hired, or rejected candidate cards."""
    status = getattr(candidate, "status", None)
    is_active = status == Status.ACTIVE or str(status).lower() == "active"
    is_hired = status == Status.HIRED or str(status).lower() == "hired"

    if is_active:
        dur_str = format_duration(getattr(candidate, "time_in_stage_seconds", None))
        return f"In stage {dur_str}"

    current_time = now or datetime.now(UTC)
    stage_entered_at = getattr(candidate, "stage_entered_at", current_time)

    # Ensure tz-aware comparison
    if stage_entered_at.tzinfo is None:
        stage_entered_at = stage_entered_at.replace(tzinfo=UTC)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=UTC)

    secs = max(0.0, (current_time - stage_entered_at).total_seconds())
    dur = format_duration(secs)

    if is_hired:
        return f"Hired {dur} ago" if dur != "just now" else "Hired just now"

    stage = getattr(candidate, "stage", "")
    stage_name = stage.value if hasattr(stage, "value") else str(stage)
    if dur != "just now":
        return f"Rejected at {stage_name} · {dur} ago"
    return f"Rejected at {stage_name} · just now"

"""Display formatting helpers for duration, badge styling, and audit events.

SYSTEM_DESIGN §13.1.
"""

from datetime import UTC, datetime
from typing import Any

from app.core.timeutil import resolve_tz
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


def format_datetime(dt: datetime, tz_str: str = "Asia/Kolkata") -> str:
    """Format datetime in candidate/recruiter timezone."""
    zone = resolve_tz(tz_str, "Asia/Kolkata")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    local_dt = dt.astimezone(zone)
    return local_dt.strftime("%b %d, %Y %H:%M")


def format_event_description(event: Any) -> str:
    """Return human-readable description for audit timeline event."""
    ev_type = getattr(event, "type", "")
    type_str = ev_type.value if hasattr(ev_type, "value") else str(ev_type)
    from_s = getattr(event, "from_stage", None)
    to_s = getattr(event, "to_stage", None)
    from_str = from_s.value if hasattr(from_s, "value") and from_s else str(from_s or "")
    to_str = to_s.value if hasattr(to_s, "value") and to_s else str(to_s or "")

    if type_str.lower() == "created":
        return f"Created in {to_str or 'Applied'}"
    if type_str.lower() == "advanced":
        if from_str and to_str:
            return f"Advanced from {from_str} to {to_str}"
        return f"Advanced to {to_str}"
    if type_str.lower() == "rejected":
        return f"Rejected at {from_str or 'stage'}"
    if type_str.lower() == "note":
        note_text = getattr(event, "note", "") or ""
        return f"Note added: {note_text}"
    return type_str

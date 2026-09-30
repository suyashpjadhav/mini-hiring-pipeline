"""Tests for render.py template rendering helper and timezone resolution (Step 10)."""

from fastapi import Request
from starlette.datastructures import Headers

from app.core.config import Settings
from app.web.render import render, resolve_request_tz


def test_timezone_resolution_priority() -> None:
    """Verify timezone resolution order: X-Timezone header > tz cookie > default."""
    default_tz = "Asia/Kolkata"

    # 1. Header present
    req_header = Request(
        scope={
            "type": "http",
            "headers": Headers(
                {"X-Timezone": "America/New_York", "cookie": "tz=Europe/London"}
            ).raw,
        }
    )
    assert resolve_request_tz(req_header, default_tz) == "America/New_York"

    # 2. Cookie present (no header)
    req_cookie = Request(
        scope={
            "type": "http",
            "headers": Headers({"cookie": "tz=Europe/London"}).raw,
        }
    )
    assert resolve_request_tz(req_cookie, default_tz) == "Europe/London"

    # 3. Neither present -> default
    req_none = Request(
        scope={
            "type": "http",
            "headers": Headers({}).raw,
        }
    )
    assert resolve_request_tz(req_none, default_tz) == "Asia/Kolkata"

    # 4. Invalid value -> fallback to default
    req_invalid = Request(
        scope={
            "type": "http",
            "headers": Headers(
                {"X-Timezone": "Invalid/Zone_Name", "cookie": "tz=Also/Invalid"}
            ).raw,
        }
    )
    assert resolve_request_tz(req_invalid, default_tz) == "Asia/Kolkata"


def test_render_hx_trigger_toast() -> None:
    """Verify render sets the HX-Trigger header format when toast parameter is provided."""
    settings = Settings(app_env="test")

    class DummyApp:
        state = type("State", (), {"settings": settings})()

    req = Request(
        scope={
            "type": "http",
            "headers": Headers({}).raw,
            "app": DummyApp(),
        }
    )
    req.state.csrf_token = "sample_value"  # noqa: S105

    response = render(req, "pages/index.html", {"total": 10}, toast=("success", "Candidate added!"))

    assert response.status_code == 200
    assert "HX-Trigger" in response.headers
    expected_trigger = '{"toast": {"kind": "success", "message": "Candidate added!"}}'
    assert response.headers["HX-Trigger"] == expected_trigger

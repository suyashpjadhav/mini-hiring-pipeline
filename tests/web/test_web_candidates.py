"""Tests for candidate web routes: add, advance, reject, stale version, and CSRF/CSP (Step 11)."""

import json

from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.clock import FixedClock
from app.features.pipeline.service import PipelineService


def test_add_candidate_success_and_validation_errors(client: TestClient) -> None:
    """Verify POST /ui/candidates success returns board + triggers + toast,
    and validation error returns dialog with retarget.
    """
    # Step 1: GET / to obtain CSRF token cookie
    res_get = client.get("/")
    assert res_get.status_code == 200
    csrf_token = client.cookies.get("csrftoken")
    assert csrf_token is not None

    headers = {"X-CSRF-Token": csrf_token}

    # Step 2: Invalid POST - empty name
    res_invalid_name = client.post(
        "/ui/candidates",
        data={"full_name": "", "email": "test@example.com"},
        headers=headers,
    )
    assert res_invalid_name.status_code == 200
    assert res_invalid_name.headers.get("HX-Retarget") == "#dialog"
    assert res_invalid_name.headers.get("HX-Reswap") == "innerHTML"
    assert "Full name is required" in res_invalid_name.text

    # Step 3: Invalid POST - malformed email
    res_invalid_email = client.post(
        "/ui/candidates",
        data={"full_name": "Valid Name", "email": "not-an-email"},
        headers=headers,
    )
    assert res_invalid_email.status_code == 200
    assert res_invalid_email.headers.get("HX-Retarget") == "#dialog"
    assert res_invalid_email.headers.get("HX-Reswap") == "innerHTML"
    assert "Invalid email address" in res_invalid_email.text

    # Step 4: Valid POST - success
    res_success = client.post(
        "/ui/candidates",
        data={"full_name": "Jane Doe", "email": "jane@example.com"},
        headers=headers,
    )
    assert res_success.status_code == 200
    assert "Jane Doe" in res_success.text

    trigger_header = res_success.headers.get("HX-Trigger", "")
    assert trigger_header != ""
    triggers = json.loads(trigger_header)
    assert "close-dialog" in triggers
    assert triggers.get("toast", {}).get("message") == "Added Jane Doe"
    assert triggers.get("toast", {}).get("kind") == "success"


def test_advance_and_reject_actions(client: TestClient) -> None:
    """Verify POST advance and reject routes update board and issue toasts."""
    assert isinstance(client.app, FastAPI)
    app = client.app
    clock: FixedClock = app.state.clock
    service = PipelineService(app.state.engine, clock)

    # Seed a candidate
    cand = service.create_candidate("Test Candidate", "test@example.com")

    # Get CSRF token
    res_get = client.get("/")
    assert res_get.status_code == 200
    csrf_token = client.cookies.get("csrftoken")
    assert csrf_token is not None
    headers = {"X-CSRF-Token": csrf_token}

    # Advance candidate from Applied to Screening
    res_advance = client.post(
        f"/ui/candidates/{cand.id}/advance",
        data={"expected_version": 1},
        headers=headers,
    )
    assert res_advance.status_code == 200
    triggers = json.loads(res_advance.headers.get("HX-Trigger", "{}"))
    assert triggers.get("toast", {}).get("message") == "Test Candidate moved to Screening"

    # Reject candidate from Screening
    res_reject = client.post(
        f"/ui/candidates/{cand.id}/reject",
        data={"expected_version": 2},
        headers=headers,
    )
    assert res_reject.status_code == 200
    triggers = json.loads(res_reject.headers.get("HX-Trigger", "{}"))
    assert triggers.get("toast", {}).get("message") == "Test Candidate rejected at Screening"


def test_stale_expected_version_error_toast(client: TestClient) -> None:
    """Verify stale expected_version returns 200, unchanged board, and an error toast."""
    assert isinstance(client.app, FastAPI)
    app = client.app
    clock: FixedClock = app.state.clock
    service = PipelineService(app.state.engine, clock)

    cand = service.create_candidate("Stale User", "stale@example.com")

    client.get("/")
    csrf_token = client.cookies.get("csrftoken")
    headers = {"X-CSRF-Token": csrf_token}

    # Pass stale version 99
    res_stale = client.post(
        f"/ui/candidates/{cand.id}/advance",
        data={"expected_version": 99},
        headers=headers,
    )
    assert res_stale.status_code == 200
    triggers = json.loads(res_stale.headers.get("HX-Trigger", "{}"))
    toast = triggers.get("toast", {})
    assert toast.get("kind") == "error"
    msg = toast.get("message", "").lower()
    assert "changed since you loaded" in msg or "stale" in msg


def test_invalid_candidate_id_not_found_toast(client: TestClient) -> None:
    """Verify invalid candidate id returns 200, current board, and an error toast."""
    client.get("/")
    csrf_token = client.cookies.get("csrftoken")
    headers = {"X-CSRF-Token": csrf_token}

    res_not_found = client.post(
        "/ui/candidates/non_existent_id/advance",
        data={"expected_version": 1},
        headers=headers,
    )
    assert res_not_found.status_code == 200
    triggers = json.loads(res_not_found.headers.get("HX-Trigger", "{}"))
    toast = triggers.get("toast", {})
    assert toast.get("kind") == "error"
    assert "not found" in toast.get("message", "").lower()


def test_post_without_csrf_forbidden(client: TestClient) -> None:
    """Verify POST without CSRF header returns 403 Forbidden."""
    res = client.post("/ui/candidates", data={"full_name": "No CSRF"})
    assert res.status_code == 403


def test_rendered_html_csp_cleanliness(client: TestClient) -> None:
    """Verify rendered board and dialog HTML contain no inline scripts, style, or handlers."""
    res_board = client.get("/ui/board")
    assert res_board.status_code == 200

    soup_board = BeautifulSoup(res_board.text, "html.parser")
    assert soup_board.find_all("script") == []
    for tag in soup_board.find_all(True):
        assert "style" not in tag.attrs
        for attr in tag.attrs:
            msg = f"Found inline event handler '{attr}' on tag <{tag.name}>"
            assert not attr.startswith("on"), msg

    res_dialog = client.get("/ui/candidates/new")
    assert res_dialog.status_code == 200
    soup_dialog = BeautifulSoup(res_dialog.text, "html.parser")
    assert soup_dialog.find_all("script") == []
    for tag in soup_dialog.find_all(True):
        assert "style" not in tag.attrs
        for attr in tag.attrs:
            msg = f"Found inline event handler '{attr}' on tag <{tag.name}>"
            assert not attr.startswith("on"), msg

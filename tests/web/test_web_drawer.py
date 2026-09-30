"""Tests for candidate drawer and audit timeline web routes (Step 12)."""

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.features.pipeline.service import PipelineService


def test_get_candidate_drawer_success(client: TestClient) -> None:
    """GET /ui/candidates/{id} returns drawer template with full history timeline."""
    assert isinstance(client.app, FastAPI)
    app = client.app
    service = PipelineService(app.state.engine, app.state.clock)
    candidate = service.create_candidate(full_name="Priya Sharma", email="priya@example.com")

    res = client.get(f"/ui/candidates/{candidate.id}")
    assert res.status_code == 200
    assert "Priya Sharma" in res.text
    assert "priya@example.com" in res.text
    assert "Created in Applied" in res.text
    assert "History verified" in res.text
    assert '<aside class="drawer"' in res.text


def test_get_candidate_drawer_unknown_id(client: TestClient) -> None:
    """GET /ui/candidates/invalid-id returns empty response with error toast trigger."""
    res = client.get("/ui/candidates/non-existent-id")
    assert res.status_code == 200
    assert res.text == ""
    trigger_header = res.headers.get("HX-Trigger", "")
    assert trigger_header != ""
    triggers = json.loads(trigger_header)
    assert "toast" in triggers
    assert triggers["toast"]["kind"] == "error"


def test_close_drawer_and_dialog_routes(client: TestClient) -> None:
    """GET /ui/drawer/close and GET /ui/dialog/close return 200 with empty body."""
    res_drawer = client.get("/ui/drawer/close")
    assert res_drawer.status_code == 200
    assert res_drawer.text == ""

    res_dialog = client.get("/ui/dialog/close")
    assert res_dialog.status_code == 200
    assert res_dialog.text == ""


def test_add_note_success_and_board_refresh_trigger(client: TestClient) -> None:
    """POST /ui/candidates/{id}/notes appends note, triggers board-refresh event and toast."""
    assert isinstance(client.app, FastAPI)
    app = client.app
    service = PipelineService(app.state.engine, app.state.clock)
    candidate = service.create_candidate(full_name="Rahul Verma", email="rahul@example.com")
    initial_version = candidate.version

    client.get("/")
    csrf_token = client.cookies.get("csrftoken")
    assert csrf_token is not None

    headers = {"X-CSRF-Token": csrf_token}

    res_note = client.post(
        f"/ui/candidates/{candidate.id}/notes",
        data={"note": "Great background in distributed systems."},
        headers=headers,
    )
    assert res_note.status_code == 200
    assert "Great background in distributed systems." in res_note.text
    assert "Note added: Great background in distributed systems." in res_note.text

    trigger_header = res_note.headers.get("HX-Trigger", "")
    assert trigger_header != ""
    triggers = json.loads(trigger_header)
    assert "board-refresh" in triggers
    assert "toast" in triggers
    assert triggers["toast"]["message"] == "Note added"

    # Verify board shows updated candidate version
    res_board = client.get("/ui/board")
    assert res_board.status_code == 200
    expected_val = f'value="{initial_version + 1}"'
    assert expected_val in res_board.text


def test_add_note_validation_error(client: TestClient) -> None:
    """POST /ui/candidates/{id}/notes with empty text returns inline error in drawer."""
    assert isinstance(client.app, FastAPI)
    app = client.app
    service = PipelineService(app.state.engine, app.state.clock)
    candidate = service.create_candidate(full_name="Ananya Roy", email="ananya@example.com")

    client.get("/")
    csrf_token = client.cookies.get("csrftoken")
    assert csrf_token is not None

    headers = {"X-CSRF-Token": csrf_token}

    res_empty = client.post(
        f"/ui/candidates/{candidate.id}/notes",
        data={"note": "   "},
        headers=headers,
    )
    assert res_empty.status_code == 200
    assert "Note text cannot be empty" in res_empty.text

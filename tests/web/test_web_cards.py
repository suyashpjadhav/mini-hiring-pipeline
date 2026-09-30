"""Tests for candidate card rendering and final outcome card invariants (Step 11)."""

from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.clock import FixedClock
from app.features.pipeline.domain.stages import Action
from app.features.pipeline.service import PipelineService


def test_final_outcome_cards_no_buttons(client: TestClient) -> None:
    """Verify Hired and Rejected cards contain no <form> and no <button> elements."""
    assert isinstance(client.app, FastAPI)
    app = client.app
    clock: FixedClock = app.state.clock
    service = PipelineService(app.state.engine, clock)

    # 1. Hired candidate
    c_hired = service.create_candidate("Grace Hired", "grace@example.com")
    service.transition(c_hired.id, Action.ADVANCE, expected_version=1)  # Screening
    service.transition(c_hired.id, Action.ADVANCE, expected_version=2)  # Interview
    service.transition(c_hired.id, Action.ADVANCE, expected_version=3)  # Offer
    service.transition(c_hired.id, Action.ADVANCE, expected_version=4)  # Hired

    # 2. Rejected candidate
    c_rej = service.create_candidate("Harry Rejected", "harry@example.com")
    service.transition(c_rej.id, Action.ADVANCE, expected_version=1)  # Screening
    service.transition(c_rej.id, Action.REJECT, expected_version=2)  # Rejected at Screening

    res = client.get("/ui/board")
    assert res.status_code == 200

    soup = BeautifulSoup(res.text, "html.parser")

    # Assert Hired card properties
    card_hired = soup.find("article", attrs={"data-id": c_hired.id})
    assert card_hired is not None
    assert card_hired.find_all("form") == []
    assert card_hired.find_all("button") == []
    badge_hired = card_hired.find("span", class_="badge")
    assert badge_hired is not None
    assert "Hired" in badge_hired.text

    # Assert Rejected card properties
    card_rej = soup.find("article", attrs={"data-id": c_rej.id})
    assert card_rej is not None
    assert card_rej.find_all("form") == []
    assert card_rej.find_all("button") == []
    badge_rej = card_rej.find("span", class_="badge")
    assert badge_rej is not None
    assert "Rejected at Screening" in badge_rej.text

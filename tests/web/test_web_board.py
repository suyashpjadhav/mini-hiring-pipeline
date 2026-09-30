"""Tests for web Kanban board rendering and column counts (Step 11)."""

from datetime import timedelta

from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.clock import FixedClock
from app.features.pipeline.domain.stages import Action
from app.features.pipeline.service import PipelineService


def test_board_render_columns_and_counts(client: TestClient) -> None:
    """Verify board renders 6 columns with correct counts and badge classes (FixedClock)."""
    assert isinstance(client.app, FastAPI)
    app = client.app
    clock: FixedClock = app.state.clock
    now = clock.now()

    # Seed candidates at different times to test badge classes
    service = PipelineService(app.state.engine, clock)

    # 1. Applied (< 3d -> sage)
    clock.set(now - timedelta(days=1))
    c_applied = service.create_candidate("Alice Applied", "alice@example.com")

    # 2. Screening (3-7d -> ochre)
    clock.set(now - timedelta(days=4))
    c_screen = service.create_candidate("Bob Screen", "bob@example.com")
    service.transition(c_screen.id, Action.ADVANCE, expected_version=1)

    # 3. Interview (> 7d -> terracotta)
    clock.set(now - timedelta(days=10))
    c_inter = service.create_candidate("Charlie Interview", "charlie@example.com")
    service.transition(c_inter.id, Action.ADVANCE, expected_version=1)
    service.transition(c_inter.id, Action.ADVANCE, expected_version=2)

    # 4. Offer
    clock.set(now - timedelta(days=2))
    c_offer = service.create_candidate("David Offer", "david@example.com")
    service.transition(c_offer.id, Action.ADVANCE, expected_version=1)
    service.transition(c_offer.id, Action.ADVANCE, expected_version=2)
    service.transition(c_offer.id, Action.ADVANCE, expected_version=3)

    # 5. Hired
    clock.set(now - timedelta(days=5))
    c_hired = service.create_candidate("Eve Hired", "eve@example.com")
    service.transition(c_hired.id, Action.ADVANCE, expected_version=1)
    service.transition(c_hired.id, Action.ADVANCE, expected_version=2)
    service.transition(c_hired.id, Action.ADVANCE, expected_version=3)
    service.transition(c_hired.id, Action.ADVANCE, expected_version=4)

    # 6. Rejected from Screening
    clock.set(now - timedelta(days=6))
    c_rej = service.create_candidate("Frank Rejected", "frank@example.com")
    service.transition(c_rej.id, Action.ADVANCE, expected_version=1)
    service.transition(c_rej.id, Action.REJECT, expected_version=2)

    clock.set(now)

    res = client.get("/ui/board")
    assert res.status_code == 200

    soup = BeautifulSoup(res.text, "html.parser")
    grid = soup.find("div", class_="board-grid")
    assert grid is not None

    sections = grid.find_all("section", class_="board-column")
    assert len(sections) == 6

    column_titles = []
    for s in sections:
        h2 = s.find("h2", class_="column-title")
        assert h2 is not None
        column_titles.append(" ".join(h2.text.split()))

    assert any("Applied (1)" in title for title in column_titles)
    assert any("Screening (1)" in title for title in column_titles)
    assert any("Interview (1)" in title for title in column_titles)
    assert any("Offer (1)" in title for title in column_titles)
    assert any("Hired (1)" in title for title in column_titles)
    assert any("Rejected (1)" in title for title in column_titles)

    # Verify badge classes
    card_applied = soup.find("article", attrs={"data-id": c_applied.id})
    assert card_applied is not None
    badge_applied = card_applied.find("span", class_="badge")
    assert badge_applied is not None
    assert "badge-sage" in str(badge_applied.get("class"))

    card_screen = soup.find("article", attrs={"data-id": c_screen.id})
    assert card_screen is not None
    badge_screen = card_screen.find("span", class_="badge")
    assert badge_screen is not None
    assert "badge-ochre" in str(badge_screen.get("class"))

    card_inter = soup.find("article", attrs={"data-id": c_inter.id})
    assert card_inter is not None
    badge_inter = card_inter.find("span", class_="badge")
    assert badge_inter is not None
    assert "badge-terracotta" in str(badge_inter.get("class"))

"""Tests for web Kanban board stage bar, view routing, and section rendering (Step 11)."""

from datetime import timedelta

from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.clock import FixedClock
from app.features.pipeline.domain.stages import Action
from app.features.pipeline.service import PipelineService


def test_board_stage_bar_and_view_routing(client: TestClient) -> None:
    """Verify stage bar has 7 items, correct counts (All includes rejected),
    view=all renders 6 sections, and single stage views work correctly.
    """
    assert isinstance(client.app, FastAPI)
    app = client.app
    clock: FixedClock = app.state.clock
    now = clock.now()

    service = PipelineService(app.state.engine, clock)

    # Seed 6 candidates (1 in each stage/status)
    clock.set(now - timedelta(days=1))
    c_applied = service.create_candidate("Alice Applied", "alice@example.com")

    clock.set(now - timedelta(days=4))
    c_screen = service.create_candidate("Bob Screen", "bob@example.com")
    service.transition(c_screen.id, Action.ADVANCE, expected_version=1)

    clock.set(now - timedelta(days=10))
    c_inter = service.create_candidate("Charlie Interview", "charlie@example.com")
    service.transition(c_inter.id, Action.ADVANCE, expected_version=1)
    service.transition(c_inter.id, Action.ADVANCE, expected_version=2)

    clock.set(now - timedelta(days=2))
    c_offer = service.create_candidate("David Offer", "david@example.com")
    service.transition(c_offer.id, Action.ADVANCE, expected_version=1)
    service.transition(c_offer.id, Action.ADVANCE, expected_version=2)
    service.transition(c_offer.id, Action.ADVANCE, expected_version=3)

    clock.set(now - timedelta(days=5))
    c_hired = service.create_candidate("Eve Hired", "eve@example.com")
    service.transition(c_hired.id, Action.ADVANCE, expected_version=1)
    service.transition(c_hired.id, Action.ADVANCE, expected_version=2)
    service.transition(c_hired.id, Action.ADVANCE, expected_version=3)
    service.transition(c_hired.id, Action.ADVANCE, expected_version=4)

    clock.set(now - timedelta(days=6))
    c_rej = service.create_candidate("Frank Rejected", "frank@example.com")
    service.transition(c_rej.id, Action.ADVANCE, expected_version=1)
    service.transition(c_rej.id, Action.REJECT, expected_version=2)

    clock.set(now)

    # 1. GET /ui/board (default view=all)
    res = client.get("/ui/board")
    assert res.status_code == 200

    soup = BeautifulSoup(res.text, "html.parser")
    nav = soup.find("nav", attrs={"aria-label": "Pipeline stages"})
    assert nav is not None

    items = nav.find_all("a", class_="stage-bar-item")
    assert len(items) == 7

    # Check item text and counts
    stage_bar_texts = [" ".join(item.text.split()) for item in items]
    assert "All 6" in stage_bar_texts[0]
    assert "Applied 1" in stage_bar_texts[1]
    assert "Screening 1" in stage_bar_texts[2]
    assert "Interview 1" in stage_bar_texts[3]
    assert "Offer 1" in stage_bar_texts[4]
    assert "Hired 1" in stage_bar_texts[5]
    assert "Rejected 1" in stage_bar_texts[6]

    # view=all has aria-current="page" on All item
    assert items[0].get("aria-current") == "page"

    # view=all renders 6 stacked sections in order
    sections = soup.find_all("section", class_="board-section")
    assert len(sections) == 6
    section_titles = []
    for s in sections:
        h2 = s.find("h2", class_="section-title")
        assert h2 is not None
        section_titles.append(" ".join(h2.text.split()))

    assert "Applied (1)" in section_titles[0]
    assert "Screening (1)" in section_titles[1]
    assert "Interview (1)" in section_titles[2]
    assert "Offer (1)" in section_titles[3]
    assert "Hired (1)" in section_titles[4]
    assert "Rejected (1)" in section_titles[5]

    # 2. view=Screening (case exact)
    res_screening = client.get("/ui/board?view=Screening")
    assert res_screening.status_code == 200
    soup_scr = BeautifulSoup(res_screening.text, "html.parser")
    sections_scr = soup_scr.find_all("section", class_="board-section")
    assert len(sections_scr) == 1
    h2_scr = sections_scr[0].find("h2")
    assert h2_scr is not None
    assert "Screening · 1" in h2_scr.text
    assert soup_scr.find("article", attrs={"data-id": c_screen.id}) is not None
    assert soup_scr.find("article", attrs={"data-id": c_applied.id}) is None

    # 3. view=screening (lowercase) works and maps to Screening
    res_lower = client.get("/ui/board?view=screening")
    assert res_lower.status_code == 200
    soup_low = BeautifulSoup(res_lower.text, "html.parser")
    sections_low = soup_low.find_all("section", class_="board-section")
    assert len(sections_low) == 1
    h2_low = sections_low[0].find("h2")
    assert h2_low is not None
    assert "Screening · 1" in h2_low.text

    # 4. view=bogus maps to view=all
    res_bogus = client.get("/ui/board?view=bogus")
    assert res_bogus.status_code == 200
    soup_bogus = BeautifulSoup(res_bogus.text, "html.parser")
    sections_bogus = soup_bogus.find_all("section", class_="board-section")
    assert len(sections_bogus) == 6


def test_full_page_view_routing(client: TestClient) -> None:
    """Verify full-page GET /?view=Interview renders Interview view with aria-current."""
    assert isinstance(client.app, FastAPI)
    res = client.get("/?view=Interview")
    assert res.status_code == 200

    soup = BeautifulSoup(res.text, "html.parser")
    nav = soup.find("nav", attrs={"aria-label": "Pipeline stages"})
    assert nav is not None

    item_interview = nav.find("a", attrs={"href": "/?view=Interview"})
    assert item_interview is not None
    assert item_interview.get("aria-current") == "page"
    assert "is-active" in str(item_interview.get("class"))

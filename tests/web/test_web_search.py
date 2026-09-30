"""Web search integration tests (Step 14)."""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from scripts.seed import seed_database


def seed_test_database(client: TestClient) -> None:
    """Seed test database with seed_data.json at NOW_A reference clock."""
    from fastapi import FastAPI

    assert isinstance(client.app, FastAPI)
    app: FastAPI = client.app
    now_a = datetime(2026, 9, 30, 14, 0, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    app.state.clock.set(now_a)
    seed_json_path = Path(__file__).parent.parent.parent / "scripts" / "seed_data.json"
    seed_database(app.state.engine, seed_json_path, now_a, ZoneInfo("Asia/Kolkata"))


def test_sharam_search_order_and_reasons(client: TestClient) -> None:
    """Verify 'sharam' returns Priya Sharma, Priyanka Sharma, Riya Sharman with name reasons."""
    seed_test_database(client)

    res = client.get("/ui/search?q=sharam")
    assert res.status_code == 200

    soup = BeautifulSoup(res.text, "html.parser")
    cards = soup.find_all("article", class_="candidate-card")
    assert len(cards) == 3

    names = []
    for card in cards:
        btn = card.find("button", class_="card-name")
        assert btn is not None
        names.append(" ".join(btn.text.split()))

    assert names == ["Priya Sharma", "Priyanka Sharma", "Riya Sharman"]

    # Verify name reasons are present on Priya Sharma card
    priya_card = cards[0]
    reasons = priya_card.find("ul", class_="search-reasons")
    assert reasons is not None
    assert "sharam" in reasons.text


def test_stuck_in_hired_error_card(client: TestClient) -> None:
    """Verify 'stuck in hired' produces an error card with FINAL_STAGE_STUCK message."""
    seed_test_database(client)

    res = client.get("/ui/search?q=stuck%20in%20hired")
    assert res.status_code == 200

    soup = BeautifulSoup(res.text, "html.parser")
    err_card = soup.find("div", class_="search-card-error")
    assert err_card is not None
    assert "Hired is a final outcome" in err_card.text


def test_combo4_empty_result_hint(client: TestClient) -> None:
    """Verify combo-4 query produces EMPTY_RESULT hint containing 'there would be 4'."""
    seed_test_database(client)

    q = "in screening for more than 5 days and added this week"
    res = client.get(f"/ui/search?q={q}")
    assert res.status_code == 200

    soup = BeautifulSoup(res.text, "html.parser")
    hint_card = soup.find("div", class_="search-card-hint")
    assert hint_card is not None
    assert "there would be 4" in hint_card.text


def test_empty_query_returns_board(client: TestClient) -> None:
    """Verify empty q returns the board partial."""
    seed_test_database(client)

    res1 = client.get("/ui/search?q=")
    assert res1.status_code == 200
    soup1 = BeautifulSoup(res1.text, "html.parser")
    assert soup1.find("div", id="board") is not None
    assert soup1.find("nav", attrs={"aria-label": "Pipeline stages"}) is not None

    res2 = client.get("/ui/search")
    assert res2.status_code == 200
    soup2 = BeautifulSoup(res2.text, "html.parser")
    assert soup2.find("div", id="board") is not None


def test_result_names_carry_drawer_hx_attributes(client: TestClient) -> None:
    """Verify result candidate names carry drawer hx-get, hx-target, hx-swap."""
    seed_test_database(client)

    res = client.get("/ui/search?q=sharam")
    assert res.status_code == 200

    soup = BeautifulSoup(res.text, "html.parser")
    name_btns = soup.find_all("button", class_="card-name")
    assert len(name_btns) > 0

    for btn in name_btns:
        hx_get = str(btn.get("hx-get"))
        assert hx_get.startswith("/ui/candidates/")
        assert btn.get("hx-target") == "#drawer"
        assert btn.get("hx-swap") == "innerHTML"


def test_csp_cleanliness_and_htmx_attributes(client: TestClient) -> None:
    """Verify CSP cleanliness (no inline script, no style attrs, no on*) and hx target/swap."""
    seed_test_database(client)

    for q in [
        "sharam",
        "stuck in hired",
        "in screening for more than 5 days and added this week",
        "xqzt",
    ]:
        res = client.get(f"/ui/search?q={q}")
        assert res.status_code == 200

        soup = BeautifulSoup(res.text, "html.parser")

        # 1. No <script> tags
        assert len(soup.find_all("script")) == 0, f"Found <script> in response for q='{q}'"

        # 2. No style="..." attributes
        style_elements = [el for el in soup.find_all(True) if el.get("style") is not None]
        assert len(style_elements) == 0, f"Found style attribute in response for q='{q}'"

        # 3. No on* event handler attributes
        for tag in soup.find_all(True):
            for attr in tag.attrs:
                assert not attr.startswith("on"), f"Found inline event handler {attr} in q='{q}'"

        # 4. Every hx-get/post/put/delete has explicit hx-target and hx-swap
        verbs = ["hx-get", "hx-post", "hx-put", "hx-delete", "hx-patch"]
        for tag in soup.find_all(True):
            has_hx_verb = any(attr in tag.attrs for attr in verbs)
            if has_hx_verb:
                assert tag.get("hx-target") is not None, f"Missing hx-target on {tag} for q='{q}'"
                assert tag.get("hx-swap") is not None, f"Missing hx-swap on {tag} for q='{q}'"

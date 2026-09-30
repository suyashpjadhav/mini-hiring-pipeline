"""Tests for web base template rendering, CSP HTML standards, and static serving (Step 10)."""

from bs4 import BeautifulSoup
from fastapi.testclient import TestClient


def test_base_layout_structure(client: TestClient) -> None:
    """Verify / returns 200 with csrf meta, htmx-config meta, and scripts in correct order."""
    res = client.get("/")
    assert res.status_code == 200

    soup = BeautifulSoup(res.text, "html.parser")

    # Meta tags
    csrf_meta = soup.find("meta", {"name": "csrf-token"})
    assert csrf_meta is not None
    assert csrf_meta.get("content")

    htmx_meta = soup.find("meta", {"name": "htmx-config"})
    assert htmx_meta is not None
    assert "allowEval" in str(htmx_meta.get("content", ""))
    assert "disableInheritance" in str(htmx_meta.get("content", ""))

    # Drawer container outside #board check
    drawer_el = soup.find("div", {"id": "drawer"})
    assert drawer_el is not None
    board_el = soup.find("div", {"id": "board"})
    assert board_el is not None
    assert drawer_el not in board_el.find_all(True)

    # External scripts order check
    scripts = soup.find_all("script")
    script_sources = [s.get("src") for s in scripts if s.get("src")]

    assert len(script_sources) == 3
    assert script_sources[0] == "/static/vendor/htmx.min.js"
    assert script_sources[1] == "/static/js/app.js"
    assert script_sources[2] == "/static/vendor/alpine-csp.min.js"

    for script in scripts:
        assert script.has_attr("defer")


def test_no_inline_scripts_styles_or_handlers(client: TestClient) -> None:
    """Verify HTML contains NO inline <script>, NO style attributes, and NO on* event handlers."""
    res = client.get("/")
    soup = BeautifulSoup(res.text, "html.parser")

    # 1. No inline <script> (scripts without src attribute)
    inline_scripts = [s for s in soup.find_all("script") if not s.get("src")]
    assert len(inline_scripts) == 0

    # 2. No elements with a style attribute
    elements_with_style = soup.find_all(lambda tag: tag.has_attr("style"))
    assert len(elements_with_style) == 0

    # 3. No on* event handler attributes or hx-on
    elements_with_on_attr: list[str] = []
    for tag in soup.find_all(True):
        for attr in tag.attrs:
            attr_lower = str(attr).lower()
            if attr_lower.startswith("on") or attr_lower.startswith("hx-on"):
                elements_with_on_attr.append(f"<{tag.name} {attr}=...>")

    assert len(elements_with_on_attr) == 0, f"Found inline event handlers: {elements_with_on_attr}"


def test_static_files_served(client: TestClient) -> None:
    """Verify /static/vendor/htmx.min.js and font file return 200."""
    res_htmx = client.get("/static/vendor/htmx.min.js")
    assert res_htmx.status_code == 200
    assert "htmx" in res_htmx.text

    res_font = client.get("/static/fonts/poppins-400.woff2")
    assert res_font.status_code == 200
    assert len(res_font.content) > 1000

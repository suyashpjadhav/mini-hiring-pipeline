"""API and page integration tests for health, docs, and index routes."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    """Test GET /api/v1/health returns 200 and expected JSON structure."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["llm"] in ("enabled", "disabled")


def test_docs_endpoint() -> None:
    """Test GET /docs returns 200 OK."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_index_page_endpoint() -> None:
    """Test GET / returns 200 HTML content without inline script tags."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<title>Mini Hiring Pipeline</title>" in response.text
    assert "<script" not in response.text.lower()

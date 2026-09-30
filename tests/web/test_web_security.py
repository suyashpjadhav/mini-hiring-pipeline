"""Tests for web security middleware: CSP, CSRF, cookie flags, and API guard (Step 10)."""

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.security import add_security_middleware


def test_csp_headers_present(client: TestClient) -> None:
    """Verify CSP header present on / and relaxed CSP present on /docs."""
    # Check root page CSP header
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "Content-Security-Policy" in res_root.headers
    csp_root = res_root.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp_root
    assert "script-src 'self'" in csp_root
    assert "https://cdn.jsdelivr.net" not in csp_root

    # Check docs page relaxed CSP header
    res_docs = client.get("/docs")
    assert res_docs.status_code == 200
    assert "Content-Security-Policy" in res_docs.headers
    csp_docs = res_docs.headers["Content-Security-Policy"]
    assert "https://cdn.jsdelivr.net" in csp_docs
    assert "'unsafe-inline'" in csp_docs

    # Check other security headers
    assert res_root.headers.get("X-Content-Type-Options") == "nosniff"
    assert res_root.headers.get("Referrer-Policy") == "same-origin"
    assert "Permissions-Policy" in res_root.headers


def test_csrf_token_required_on_posts() -> None:
    """Verify CSRF double-submit token requirement on state-changing /ui/* routes."""
    settings = Settings(app_env="test")
    test_app = FastAPI()

    @test_app.get("/ui/form")
    def get_form() -> PlainTextResponse:
        return PlainTextResponse("form")

    @test_app.post("/ui/ping")
    def ping() -> PlainTextResponse:
        return PlainTextResponse("pong")

    add_security_middleware(test_app, settings)
    with TestClient(test_app) as test_client:
        # Step 1: GET to receive csrftoken cookie
        res = test_client.get("/ui/form")
        assert res.status_code == 200
        cookie_token = test_client.cookies.get("csrftoken")
        assert cookie_token is not None

        # Step 2: POST without X-CSRF-Token header -> 403
        res_no_header = test_client.post("/ui/ping")
        assert res_no_header.status_code == 403

        # Step 3: POST with wrong X-CSRF-Token header -> 403
        res_wrong_token = test_client.post("/ui/ping", headers={"X-CSRF-Token": "invalid_token"})
        assert res_wrong_token.status_code == 403

        # Step 4: POST with matching X-CSRF-Token header -> 200
        res_valid = test_client.post("/ui/ping", headers={"X-CSRF-Token": cookie_token})
        assert res_valid.status_code == 200
        assert res_valid.text == "pong"


def test_csrf_cookie_flags(client: TestClient) -> None:
    """Verify csrftoken cookie has HttpOnly and SameSite=Strict flags."""
    res = client.get("/")
    assert res.status_code == 200

    set_cookie_header = res.headers.get("set-cookie", "").lower()
    assert "csrftoken=" in set_cookie_header
    assert "httponly" in set_cookie_header
    assert "samesite=strict" in set_cookie_header


def test_api_guard(client: TestClient) -> None:
    """Verify ApiGuardMiddleware enforces Content-Type and Origin on /api/* routes."""
    # 1. Non-JSON form-encoded POST -> 415
    res_form = client.post(
        "/api/v1/candidates",
        data={"full_name": "Form User"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert res_form.status_code == 415
    json_err = res_form.json()
    assert json_err["code"] == "UNSUPPORTED_MEDIA_TYPE"

    # 2. Cross-origin request with evil Origin -> 403
    res_evil = client.post(
        "/api/v1/candidates",
        json={"full_name": "Evil Candidate"},
        headers={"Origin": "https://evil.example"},
    )
    assert res_evil.status_code == 403
    json_evil = res_evil.json()
    assert json_evil["code"] == "FORBIDDEN_ORIGIN"

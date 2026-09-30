"""Security middleware (CSRF double-submit, security headers, API guard) (SYSTEM_DESIGN §16)."""

import hmac
import secrets
from urllib.parse import urlparse

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import Settings, get_settings

DEFAULT_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "font-src 'self'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)

# Swagger UI at /docs requires scripts and styles from jsDelivr CDN, inline initializer scripts,
# and images from FastAPI's official site.
RELAXED_DOCS_CSP = (
    "default-src 'self'; "
    "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "font-src 'self'; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)

PERMISSIONS_POLICY = (
    "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
    "magnetometer=(), microphone=(), payment=(), usb=()"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforces CSP, X-Content-Type-Options, Referrer-Policy, and Permissions-Policy headers."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        path = request.url.path
        csp = RELAXED_DOCS_CSP if path in ("/docs", "/openapi.json") else DEFAULT_CSP

        response.headers["Content-Security-Policy"] = csp
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = PERMISSIONS_POLICY
        return response


class CSRFMiddleware(BaseHTTPMiddleware):
    """Enforces double-submit CSRF token for state-changing operations on /ui/* routes."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = getattr(request.app.state, "settings", None) or get_settings()
        cookie_token = request.cookies.get("csrftoken")
        is_new_cookie = False

        if cookie_token:
            csrf_token = cookie_token
        else:
            csrf_token = secrets.token_urlsafe(32)
            is_new_cookie = True

        request.state.csrf_token = csrf_token

        path = request.url.path
        if (path.startswith("/ui/") or path == "/ui") and request.method in (
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        ):
            header_token = request.headers.get("X-CSRF-Token")
            if (
                not cookie_token
                or not header_token
                or not hmac.compare_digest(cookie_token, header_token)
            ):
                return Response(
                    content="Forbidden: CSRF token missing or invalid",
                    status_code=403,
                    media_type="text/plain",
                )

        response = await call_next(request)

        if is_new_cookie:
            response.set_cookie(
                key="csrftoken",
                value=csrf_token,
                httponly=True,
                samesite="strict",
                path="/",
                secure=(settings.app_env == "prod"),
            )

        return response


class ApiGuardMiddleware(BaseHTTPMiddleware):
    """Enforces Content-Type and same-origin restrictions for state-changing /api/* requests."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if path.startswith("/api/") and request.method in ("POST", "PUT", "PATCH", "DELETE"):
            content_type = request.headers.get("content-type", "").lower()
            if not content_type.startswith("application/json"):
                return JSONResponse(
                    status_code=415,
                    content={
                        "code": "UNSUPPORTED_MEDIA_TYPE",
                        "message": "Content-Type must be application/json",
                        "hint": None,
                    },
                )

            origin = request.headers.get("origin")
            if origin:
                origin_host = urlparse(origin).netloc.lower()
                request_host = (request.headers.get("host") or request.url.netloc).lower()
                if origin_host != request_host:
                    return JSONResponse(
                        status_code=403,
                        content={
                            "code": "FORBIDDEN_ORIGIN",
                            "message": "Cross-origin request rejected",
                            "hint": None,
                        },
                    )

        return await call_next(request)


def add_security_middleware(app: FastAPI, settings: Settings | None = None) -> None:
    """Register security middleware stack on the FastAPI application in correct order."""
    app.add_middleware(ApiGuardMiddleware)
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

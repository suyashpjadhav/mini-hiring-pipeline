"""Template rendering helpers for web routes (SYSTEM_DESIGN §10.2)."""

import json
from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.config import get_settings
from app.core.timeutil import resolve_tz

templates = Jinja2Templates(directory="app/web/templates")


def resolve_request_tz(request: Request, default: str) -> str:
    """Resolve request timezone from X-Timezone header, tz cookie, or default."""
    candidate = request.headers.get("X-Timezone") or request.cookies.get("tz")
    zone = resolve_tz(candidate, default)
    return zone.key


def render(
    request: Request,
    template_name: str,
    context: dict[str, Any],
    *,
    toast: tuple[str, str] | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    """Render Jinja2 template injecting csrf_token, job_title, and tz into context."""
    settings = getattr(request.app.state, "settings", None) or get_settings()
    csrf_token = getattr(request.state, "csrf_token", "")
    tz_str = resolve_request_tz(request, settings.app_default_tz)

    full_context = dict(context)
    full_context.setdefault("request", request)
    full_context.setdefault("csrf_token", csrf_token)
    full_context.setdefault("job_title", settings.job_title)
    full_context.setdefault("tz", tz_str)

    content = templates.get_template(template_name).render(full_context)
    response = HTMLResponse(content=content, status_code=status_code)

    if toast is not None:
        kind, message = toast
        payload = json.dumps({"toast": {"kind": kind, "message": message}})
        response.headers["HX-Trigger"] = payload

    return response

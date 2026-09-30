"""Web route handlers for search experience (SYSTEM_DESIGN §10.2, §13.2)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.features.pipeline.service import PipelineService
from app.features.search.service import SearchService
from app.web.deps import get_pipeline_service, get_search_service
from app.web.render import render, resolve_request_tz
from app.web.routes.candidates import get_board_context

router = APIRouter(tags=["web-search"])


@router.get("/ui/search", response_class=HTMLResponse)
def search_ui_route(
    request: Request,
    pipeline_service: Annotated[PipelineService, Depends(get_pipeline_service)],
    search_service: Annotated[SearchService, Depends(get_search_service)],
    q: str | None = None,
) -> HTMLResponse:
    """Render search results partial or board partial when query is empty."""
    query = (q or "").strip()
    if not query:
        context = get_board_context(pipeline_service, "all")
        return render(request, "board/_board.html", context)

    settings = getattr(request.app.state, "settings", None)
    default_tz = getattr(settings, "app_default_tz", "Asia/Kolkata") if settings else "Asia/Kolkata"
    tz_str = resolve_request_tz(request, default_tz)

    res = search_service.search(q=query, tz_name=tz_str)

    context = {
        "q": query,
        "results": res.results,
        "interpretation": res.interpretation,
        "errors": res.errors,
        "warnings": res.warnings,
        "hints": res.hints,
        "took_ms": res.took_ms,
        "n": len(res.results),
        "now": pipeline_service.clock.now(),
    }
    return render(request, "search/_results.html", context)

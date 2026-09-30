"""Web page view routes (SYSTEM_DESIGN §10.2)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.features.pipeline.service import PipelineService
from app.web.deps import get_pipeline_service
from app.web.render import render
from app.web.routes.candidates import get_board_context

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
def index_page(
    request: Request,
    service: Annotated[PipelineService, Depends(get_pipeline_service)],
    view: str | None = None,
) -> HTMLResponse:
    """Render index page shell with board."""
    context = get_board_context(service, view)
    return render(request, "pages/index.html", context)

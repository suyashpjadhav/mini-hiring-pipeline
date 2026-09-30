"""Web page view routes (SYSTEM_DESIGN §10.2)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.features.pipeline.service import PipelineService
from app.web.deps import get_pipeline_service
from app.web.render import render

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
def index_page(
    request: Request,
    service: Annotated[PipelineService, Depends(get_pipeline_service)],
) -> HTMLResponse:
    """Render index page shell with board."""
    board = service.board()
    total = (
        len(board.applied)
        + len(board.screening)
        + len(board.interview)
        + len(board.offer)
        + len(board.hired)
        + len(board.rejected)
    )
    active = len(board.applied) + len(board.screening) + len(board.interview) + len(board.offer)
    return render(
        request,
        "pages/index.html",
        {
            "board": board,
            "total": total,
            "active": active,
            "now": service.clock.now(),
        },
    )

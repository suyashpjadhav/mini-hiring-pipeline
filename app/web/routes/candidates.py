"""Web route handlers for candidate management and board updates (SYSTEM_DESIGN §10.2)."""

import json
from typing import Annotated, Final

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from pydantic import EmailStr, TypeAdapter, ValidationError

from app.features.pipeline.domain.errors import DomainError, InvalidInputError
from app.features.pipeline.domain.stages import Action, Stage
from app.features.pipeline.service import PipelineService
from app.web.deps import get_pipeline_service
from app.web.render import render

router = APIRouter(tags=["web-candidates"])
email_adapter: TypeAdapter[EmailStr] = TypeAdapter(EmailStr)

CANONICAL_VIEWS: Final[dict[str, str]] = {
    "all": "all",
    "applied": "Applied",
    "screening": "Screening",
    "interview": "Interview",
    "offer": "Offer",
    "hired": "Hired",
    "rejected": "Rejected",
}


def normalize_view(raw_view: str | None) -> str:
    """Normalize raw view string to canonical stage name or 'all'."""
    if not raw_view:
        return "all"
    key = raw_view.strip().lower()
    return CANONICAL_VIEWS.get(key, "all")


def get_board_context(
    service: PipelineService,
    raw_view: str | None = None,
) -> dict[str, object]:
    """Helper to retrieve and format Kanban board context for a given view."""
    view = normalize_view(raw_view)
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
    return {
        "board": board,
        "total": total,
        "active": active,
        "view": view,
        "now": service.clock.now(),
    }


@router.get("/ui/board", response_class=HTMLResponse)
def get_board_partial(
    request: Request,
    service: Annotated[PipelineService, Depends(get_pipeline_service)],
    view: str | None = None,
) -> HTMLResponse:
    """Render Kanban board partial."""
    context = get_board_context(service, view)
    return render(request, "board/_board.html", context)


@router.get("/ui/candidates/new", response_class=HTMLResponse)
def get_add_candidate_dialog(request: Request) -> HTMLResponse:
    """Render add candidate modal dialog template."""
    return render(
        request,
        "candidates/_add_dialog.html",
        {
            "errors": {},
            "full_name": "",
            "email": "",
        },
    )


@router.post("/ui/candidates", response_class=HTMLResponse)
def create_candidate_route(
    request: Request,
    service: Annotated[PipelineService, Depends(get_pipeline_service)],
    full_name: Annotated[str, Form()] = "",
    email: Annotated[str | None, Form()] = None,
) -> HTMLResponse:
    """Add candidate route with inline form validation and board refresh."""
    clean_name = (full_name or "").strip()
    clean_email = (email or "").strip() if email else None

    errors: dict[str, str] = {}
    if not clean_name:
        errors["full_name"] = "Full name is required"

    if clean_email:
        try:
            email_adapter.validate_python(clean_email)
        except ValidationError:
            errors["email"] = "Invalid email address"

    if errors:
        return render(
            request,
            "candidates/_add_dialog.html",
            {
                "errors": errors,
                "full_name": clean_name,
                "email": clean_email or "",
            },
            headers={"HX-Retarget": "#dialog", "HX-Reswap": "innerHTML"},
            status_code=200,
        )

    try:
        candidate = service.create_candidate(full_name=clean_name, email=clean_email)
    except DomainError as err:
        field = "email" if "email" in err.message.lower() else "full_name"
        return render(
            request,
            "candidates/_add_dialog.html",
            {
                "errors": {field: err.message},
                "full_name": clean_name,
                "email": clean_email or "",
            },
            headers={"HX-Retarget": "#dialog", "HX-Reswap": "innerHTML"},
            status_code=200,
        )

    context = get_board_context(service, "all")
    return render(
        request,
        "board/_board.html",
        context,
        toast=("success", f"Added {candidate.full_name}"),
        triggers={"close-dialog": ""},
        headers={"HX-Push-Url": "/?view=all"},
        status_code=200,
    )


@router.post("/ui/candidates/{candidate_id}/advance", response_class=HTMLResponse)
def advance_candidate_route(
    candidate_id: str,
    request: Request,
    service: Annotated[PipelineService, Depends(get_pipeline_service)],
    expected_version: Annotated[int, Form()],
    view: Annotated[str | None, Form()] = None,
) -> HTMLResponse:
    """Advance candidate stage by one step."""
    try:
        updated = service.transition(
            candidate_id=candidate_id,
            action=Action.ADVANCE,
            expected_version=expected_version,
        )
        if updated.stage == Stage.HIRED:
            toast_msg = f"{updated.full_name} was hired 🎉"
        else:
            toast_msg = f"{updated.full_name} moved to {updated.stage.value}"

        context = get_board_context(service, view)
        return render(
            request,
            "board/_board.html",
            context,
            toast=("success", toast_msg),
            status_code=200,
        )
    except DomainError as err:
        context = get_board_context(service, view)
        return render(
            request,
            "board/_board.html",
            context,
            toast=("error", err.message),
            status_code=200,
        )


@router.post("/ui/candidates/{candidate_id}/reject", response_class=HTMLResponse)
def reject_candidate_route(
    candidate_id: str,
    request: Request,
    service: Annotated[PipelineService, Depends(get_pipeline_service)],
    expected_version: Annotated[int, Form()],
    view: Annotated[str | None, Form()] = None,
) -> HTMLResponse:
    """Reject candidate from their current active stage."""
    try:
        updated = service.transition(
            candidate_id=candidate_id,
            action=Action.REJECT,
            expected_version=expected_version,
        )
        toast_msg = f"{updated.full_name} rejected at {updated.stage.value}"

        context = get_board_context(service, view)
        return render(
            request,
            "board/_board.html",
            context,
            toast=("success", toast_msg),
            status_code=200,
        )
    except DomainError as err:
        context = get_board_context(service, view)
        return render(
            request,
            "board/_board.html",
            context,
            toast=("error", err.message),
            status_code=200,
        )


@router.get("/ui/drawer/close", response_class=HTMLResponse)
def close_drawer_route() -> HTMLResponse:
    """Close candidate drawer by returning an empty 200 response."""
    return HTMLResponse(content="", status_code=200)


@router.get("/ui/dialog/close", response_class=HTMLResponse)
def close_dialog_route() -> HTMLResponse:
    """Close add candidate dialog by returning an empty 200 response."""
    return HTMLResponse(content="", status_code=200)


@router.get("/ui/candidates/{candidate_id}", response_class=HTMLResponse)
def get_candidate_drawer(
    candidate_id: str,
    request: Request,
    service: Annotated[PipelineService, Depends(get_pipeline_service)],
) -> HTMLResponse:
    """Render candidate detail drawer partial into #drawer."""
    try:
        detail = service.get_detail(candidate_id)
        return render(
            request,
            "candidates/_drawer.html",
            {
                "detail": detail,
                "note_error": None,
            },
        )
    except DomainError as err:
        payload = json.dumps({"toast": {"kind": "error", "message": err.message}})
        return HTMLResponse(
            content="",
            status_code=200,
            headers={"HX-Trigger": payload},
        )


@router.post("/ui/candidates/{candidate_id}/notes", response_class=HTMLResponse)
def add_candidate_note_route(
    candidate_id: str,
    request: Request,
    service: Annotated[PipelineService, Depends(get_pipeline_service)],
    note: Annotated[str, Form()] = "",
) -> HTMLResponse:
    """Add note correction event to candidate timeline and refresh drawer + board."""
    clean_note = (note or "").strip()
    if not clean_note:
        try:
            detail = service.get_detail(candidate_id)
            return render(
                request,
                "candidates/_drawer.html",
                {
                    "detail": detail,
                    "note_error": "Note text cannot be empty",
                },
                status_code=200,
            )
        except DomainError as err:
            payload = json.dumps({"toast": {"kind": "error", "message": err.message}})
            return HTMLResponse(
                content="",
                status_code=200,
                headers={"HX-Trigger": payload},
            )

    try:
        service.add_note(candidate_id=candidate_id, text=clean_note)
        detail = service.get_detail(candidate_id)
        return render(
            request,
            "candidates/_drawer.html",
            {
                "detail": detail,
                "note_error": None,
            },
            toast=("info", "Note added"),
            triggers={"board-refresh": ""},
            status_code=200,
        )
    except InvalidInputError as err:
        try:
            detail = service.get_detail(candidate_id)
            return render(
                request,
                "candidates/_drawer.html",
                {
                    "detail": detail,
                    "note_error": err.message,
                },
                status_code=200,
            )
        except DomainError:
            payload = json.dumps({"toast": {"kind": "error", "message": err.message}})
            return HTMLResponse(
                content="",
                status_code=200,
                headers={"HX-Trigger": payload},
            )
    except DomainError as err:
        payload = json.dumps({"toast": {"kind": "error", "message": err.message}})
        return HTMLResponse(
            content="",
            status_code=200,
            headers={"HX-Trigger": payload},
        )

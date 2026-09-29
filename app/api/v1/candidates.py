"""API v1 routers for candidate resources (SYSTEM_DESIGN §10.1)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_pipeline_service
from app.api.v1.schemas import CandidateCreate, NoteRequest, TransitionRequest
from app.core.ids import is_valid_id
from app.features.pipeline.domain.errors import NotFoundError
from app.features.pipeline.schemas import (
    BoardView,
    CandidateDetail,
    CandidateView,
    ChainVerification,
    EventView,
)
from app.features.pipeline.service import PipelineService

router = APIRouter(prefix="/api/v1/candidates", tags=["candidates"])


@router.post("", response_model=CandidateView, status_code=status.HTTP_201_CREATED)
def create_candidate(
    req: CandidateCreate,
    service: Annotated[PipelineService, Depends(get_pipeline_service)],
) -> CandidateView:
    """Create a new candidate in Applied stage."""
    email_str = str(req.email) if req.email else None
    return service.create_candidate(full_name=req.full_name, email=email_str)


@router.get("", response_model=BoardView)
def get_board(
    service: Annotated[PipelineService, Depends(get_pipeline_service)],
) -> BoardView:
    """Get candidate board columns grouped by current stage and status."""
    return service.board()


@router.get("/{id}", response_model=CandidateDetail)
def get_candidate_detail(
    id: str,
    service: Annotated[PipelineService, Depends(get_pipeline_service)],
) -> CandidateDetail:
    """Get candidate details including full timeline history and verification."""
    if not is_valid_id(id):
        raise NotFoundError(f"Candidate '{id}' not found")
    return service.get_detail(id)


@router.post("/{id}/transitions", response_model=CandidateView)
def transition_candidate(
    id: str,
    req: TransitionRequest,
    service: Annotated[PipelineService, Depends(get_pipeline_service)],
) -> CandidateView:
    """Transition candidate state (advance or reject)."""
    if not is_valid_id(id):
        raise NotFoundError(f"Candidate '{id}' not found")
    return service.transition(
        candidate_id=id,
        action=req.action,
        expected_version=req.expected_version,
        note=req.note,
    )


@router.post("/{id}/notes", response_model=EventView, status_code=status.HTTP_201_CREATED)
def add_candidate_note(
    id: str,
    req: NoteRequest,
    service: Annotated[PipelineService, Depends(get_pipeline_service)],
) -> EventView:
    """Add an audit note to candidate event history."""
    if not is_valid_id(id):
        raise NotFoundError(f"Candidate '{id}' not found")
    service.add_note(id, req.note)
    detail = service.get_detail(id)
    return detail.events[-1]


@router.get("/{id}/verify", response_model=ChainVerification)
def verify_candidate_history(
    id: str,
    service: Annotated[PipelineService, Depends(get_pipeline_service)],
) -> ChainVerification:
    """Verify hash chain integrity for candidate event history."""
    if not is_valid_id(id):
        raise NotFoundError(f"Candidate '{id}' not found")
    return service.verify(id)

"""Search API endpoint (SYSTEM_DESIGN §11, §15)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_search_service
from app.features.search import SearchResponse, SearchService

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def search_candidates(
    search_service: Annotated[SearchService, Depends(get_search_service)],
    q: Annotated[str, Query(description="Search query text")] = "",
    tz: Annotated[str, Query(description="Recruiter IANA timezone")] = "Asia/Kolkata",
) -> SearchResponse:
    """Execute search query over candidates pipeline."""
    q_stripped = q.strip()
    if not q_stripped:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_INPUT",
                "message": "Search query text cannot be empty.",
            },
        )
    if len(q) > 200:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "QUERY_TOO_LONG",
                "message": "Please keep searches under 200 characters.",
            },
        )

    return search_service.search(q=q, tz_name=tz)

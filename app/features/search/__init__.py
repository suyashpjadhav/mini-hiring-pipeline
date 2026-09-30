"""Public interface for the search feature package (SYSTEM_DESIGN §15)."""

from app.features.search.schemas import SearchResponse
from app.features.search.service import SearchService

__all__ = ["SearchResponse", "SearchService"]

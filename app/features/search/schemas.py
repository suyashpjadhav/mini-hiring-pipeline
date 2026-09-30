"""Pydantic schemas for Search API request and response (SEARCH_SPEC §11)."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.features.pipeline import CandidateView


class SearchInterpretation(BaseModel):
    source: str = "rules"
    chips: list[str] = Field(default_factory=list)
    ast: dict[str, Any] | None = None


class CandidateSearchResult(BaseModel):
    candidate: CandidateView
    score: float
    reasons: list[str] = Field(default_factory=list)


class SearchMessage(BaseModel):
    code: str
    message: str
    hint: str | None = None


class SearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    interpretation: SearchInterpretation
    results: list[CandidateSearchResult] = Field(default_factory=list)
    errors: list[SearchMessage] = Field(default_factory=list)
    warnings: list[SearchMessage] = Field(default_factory=list)
    hints: list[SearchMessage] = Field(default_factory=list)
    took_ms: float

"""Pydantic v2 request models for API v1 (SYSTEM_DESIGN §10.1)."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.features.pipeline.domain.stages import Action


class CandidateCreate(BaseModel):
    """Request model for creating a candidate."""

    full_name: str
    email: EmailStr | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        s = v.strip()
        if not (1 <= len(s) <= 100):
            raise ValueError("must be 1-100 characters")
        return s


class TransitionRequest(BaseModel):
    """Request model for state transition (advance or reject)."""

    action: Action
    expected_version: int = Field(ge=1)
    note: str | None = Field(default=None, max_length=500)

    model_config = ConfigDict(extra="forbid", frozen=True)


class NoteRequest(BaseModel):
    """Request model for adding an audit note to a candidate."""

    note: str = Field(min_length=1, max_length=500)

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("note")
    @classmethod
    def validate_note(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("note cannot be empty")
        return v

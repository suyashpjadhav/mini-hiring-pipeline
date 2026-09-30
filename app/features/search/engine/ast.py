"""Typed Search Query AST models (SYSTEM_DESIGN §11.2, SEARCH_SPEC §7)."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.features.pipeline.domain.stages import Stage, Status


class CurrentStage(BaseModel):
    kind: Literal["current_stage"] = "current_stage"
    stages: list[Stage]  # active only; OR within the list


class StatusIs(BaseModel):
    kind: Literal["status"] = "status"
    status: Status
    negate: bool = False
    at_stage: Stage | None = None


class TimeInStage(BaseModel):
    kind: Literal["time_in_stage"] = "time_in_stage"
    stage: Stage | None = None
    op: Literal["gt", "gte", "lt", "lte"]
    days: float


class MovedTo(BaseModel):
    kind: Literal["moved_to"] = "moved_to"
    target: Stage | Literal["Rejected"]
    since: datetime | None = None
    until: datetime | None = None


class Reached(BaseModel):
    kind: Literal["reached"] = "reached"
    stage: Stage
    negate: bool = False


class Added(BaseModel):
    kind: Literal["added"] = "added"
    since: datetime | None = None
    until: datetime | None = None


Clause = Annotated[
    CurrentStage | StatusIs | TimeInStage | MovedTo | Reached | Added,
    Field(discriminator="kind"),
]


class QueryAST(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    clauses: list[Clause] = []
    name_terms: list[str] = []
    source: Literal["rules", "llm"] = "rules"

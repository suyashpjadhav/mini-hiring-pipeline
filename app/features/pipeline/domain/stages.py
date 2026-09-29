"""Vocabulary of the hiring pipeline: stages, statuses, actions, event types (SYSTEM_DESIGN §6)."""

from enum import StrEnum
from typing import Final


class Stage(StrEnum):
    """A step in the pipeline. The order is defined by STAGE_ORDER, not by this class."""

    APPLIED = "Applied"
    SCREENING = "Screening"
    INTERVIEW = "Interview"
    OFFER = "Offer"
    HIRED = "Hired"


class Status(StrEnum):
    """Where a candidate stands overall. Rejected is a status, never a stage."""

    ACTIVE = "active"
    HIRED = "hired"
    REJECTED = "rejected"


class Action(StrEnum):
    """The only two things a recruiter can do to move a candidate."""

    ADVANCE = "advance"
    REJECT = "reject"


class EventType(StrEnum):
    """Kinds of entries in the append-only history."""

    CREATED = "CREATED"
    ADVANCED = "ADVANCED"
    REJECTED = "REJECTED"
    NOTE = "NOTE"


STAGE_ORDER: Final[tuple[Stage, ...]] = (
    Stage.APPLIED,
    Stage.SCREENING,
    Stage.INTERVIEW,
    Stage.OFFER,
    Stage.HIRED,
)

REACHED_BIT: Final[dict[Stage, int]] = {stage: 1 << i for i, stage in enumerate(STAGE_ORDER)}


def next_stage(stage: Stage) -> Stage | None:
    """Return the stage after `stage`, or None for Hired (the last stage)."""
    position = STAGE_ORDER.index(stage)
    if position + 1 == len(STAGE_ORDER):
        return None
    return STAGE_ORDER[position + 1]

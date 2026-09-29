"""SQLAlchemy Core Table definitions mirroring SQLite schema (SYSTEM_DESIGN §7)."""

from sqlalchemy import Column, Integer, MetaData, String, Table

metadata = MetaData()

candidates = Table(
    "candidates",
    metadata,
    Column("id", String, primary_key=True),
    Column("full_name", String, nullable=False),
    Column("name_normalized", String, nullable=False),
    Column("email", String, unique=True, nullable=True),
    Column("created_at", Integer, nullable=False),
)

stage_events = Table(
    "stage_events",
    metadata,
    Column("id", String, primary_key=True),
    Column("candidate_id", String, nullable=False),
    Column("seq", Integer, nullable=False),
    Column("type", String, nullable=False),
    Column("from_stage", String, nullable=True),
    Column("to_stage", String, nullable=True),
    Column("occurred_at", Integer, nullable=False),
    Column("actor", String, nullable=False),
    Column("note", String, nullable=True),
    Column("prev_hash", String, nullable=True),
    Column("hash", String, nullable=False),
)

candidate_state = Table(
    "candidate_state",
    metadata,
    Column("candidate_id", String, primary_key=True),
    Column("stage", String, nullable=False),
    Column("status", String, nullable=False),
    Column("stage_entered_at", Integer, nullable=False),
    Column("version", Integer, nullable=False),
    Column("reached_mask", Integer, nullable=False),
    Column("last_event_at", Integer, nullable=False),
)

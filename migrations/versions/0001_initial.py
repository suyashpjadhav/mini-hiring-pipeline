"""Initial DDL migration (SYSTEM_DESIGN §7).

Revision ID: 0001_initial
Revises: None
Create Date: 2026-09-29
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE candidates (
      id              TEXT    PRIMARY KEY CHECK (length(id) = 26),
      full_name       TEXT    NOT NULL CHECK (length(full_name) BETWEEN 1 AND 100),
      name_normalized TEXT    NOT NULL,
      email           TEXT    UNIQUE CHECK (email IS NULL OR length(email) <= 254),
      created_at      INTEGER NOT NULL
    ) STRICT;
    """)

    op.execute("""
    CREATE TABLE stage_events (
      id           TEXT    PRIMARY KEY,
      candidate_id TEXT    NOT NULL REFERENCES candidates(id),
      seq          INTEGER NOT NULL CHECK (seq >= 1),
      type         TEXT    NOT NULL CHECK (type IN ('CREATED','ADVANCED','REJECTED','NOTE')),
      from_stage   TEXT    CHECK (from_stage IN
                           ('Applied','Screening','Interview','Offer','Hired')),
      to_stage     TEXT    CHECK (to_stage IN
                           ('Applied','Screening','Interview','Offer','Hired')),
      occurred_at  INTEGER NOT NULL,
      actor        TEXT    NOT NULL DEFAULT 'recruiter',
      note         TEXT    CHECK (note IS NULL OR length(note) <= 500),
      prev_hash    TEXT,
      hash         TEXT    NOT NULL,
      UNIQUE (candidate_id, seq),
      CHECK (CASE type
        WHEN 'CREATED'  THEN seq = 1 AND from_stage IS NULL AND to_stage IS 'Applied'
        WHEN 'ADVANCED' THEN coalesce(from_stage,'') || '>' || coalesce(to_stage,'') IN
                             ('Applied>Screening','Screening>Interview','Interview>Offer','Offer>Hired')
        WHEN 'REJECTED' THEN coalesce(from_stage,'') IN ('Applied','Screening','Interview','Offer')
                             AND to_stage IS NULL
        WHEN 'NOTE'     THEN from_stage IS NULL AND to_stage IS NULL AND note IS NOT NULL
        ELSE 0 END)
    ) STRICT;
    """)

    op.execute("""
    CREATE TABLE candidate_state (
      candidate_id     TEXT    PRIMARY KEY REFERENCES candidates(id),
      stage            TEXT    NOT NULL CHECK (stage IN
                               ('Applied','Screening','Interview','Offer','Hired')),
      status           TEXT    NOT NULL CHECK (status IN ('active','hired','rejected')),
      stage_entered_at INTEGER NOT NULL,
      version          INTEGER NOT NULL CHECK (version >= 1),
      reached_mask     INTEGER NOT NULL CHECK (reached_mask BETWEEN 1 AND 31),
      last_event_at    INTEGER NOT NULL,
      CHECK ((status = 'hired') = (stage = 'Hired'))
    ) STRICT;
    """)

    op.execute("""
    CREATE TRIGGER stage_events_no_update BEFORE UPDATE ON stage_events
    BEGIN SELECT RAISE(ABORT, 'stage_events is append-only'); END;
    """)

    op.execute("""
    CREATE TRIGGER stage_events_no_delete BEFORE DELETE ON stage_events
    BEGIN SELECT RAISE(ABORT, 'stage_events is append-only'); END;
    """)

    op.execute("""
    CREATE TRIGGER candidates_no_update BEFORE UPDATE ON candidates
    BEGIN SELECT RAISE(ABORT, 'candidates are immutable; add a NOTE instead'); END;
    """)

    op.execute("""
    CREATE TRIGGER candidates_no_delete BEFORE DELETE ON candidates
    BEGIN SELECT RAISE(ABORT, 'candidates cannot be deleted'); END;
    """)

    op.execute("""
    CREATE TRIGGER stage_events_guard_transition BEFORE INSERT ON stage_events
    WHEN NEW.type IN ('ADVANCED','REJECTED')
    BEGIN
      SELECT RAISE(ABORT, 'transition does not match current state')
      WHERE NOT EXISTS (
        SELECT 1 FROM candidate_state s
        WHERE s.candidate_id = NEW.candidate_id AND s.status = 'active'
          AND s.stage = NEW.from_stage AND s.version = NEW.seq - 1);
    END;
    """)

    op.execute("CREATE INDEX ix_state_board ON candidate_state(status, stage, stage_entered_at);")
    op.execute("CREATE INDEX ix_events_moves ON stage_events(type, to_stage, occurred_at);")
    op.execute("CREATE INDEX ix_events_cand ON stage_events(candidate_id, seq);")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_events_cand;")
    op.execute("DROP INDEX IF EXISTS ix_events_moves;")
    op.execute("DROP INDEX IF EXISTS ix_state_board;")
    op.execute("DROP TRIGGER IF EXISTS stage_events_guard_transition;")
    op.execute("DROP TRIGGER IF EXISTS candidates_no_delete;")
    op.execute("DROP TRIGGER IF EXISTS candidates_no_update;")
    op.execute("DROP TRIGGER IF EXISTS stage_events_no_delete;")
    op.execute("DROP TRIGGER IF EXISTS stage_events_no_update;")
    op.execute("DROP TABLE IF EXISTS candidate_state;")
    op.execute("DROP TABLE IF EXISTS stage_events;")
    op.execute("DROP TABLE IF EXISTS candidates;")

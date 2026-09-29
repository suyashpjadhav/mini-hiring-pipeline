"""Integration tests for database triggers, constraints, FKs, and immutability."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError

from app.core.ids import new_id
from app.core.timeutil import to_epoch_ms
from app.features.pipeline.domain.stages import Action, Stage
from app.features.pipeline.service import PipelineService

COLS = (
    "id, candidate_id, seq, type, from_stage, to_stage, occurred_at, actor, note, prev_hash, hash"
)


def test_raw_sql_update_delete_fail(pipeline_service: PipelineService, engine: Engine) -> None:
    """Database triggers raise ABORT on raw UPDATE or DELETE against stage_events or candidates."""
    cand = pipeline_service.create_candidate("Test Immutability", "immutability@example.com")

    with engine.connect() as conn:
        # 1. UPDATE stage_events fails
        with pytest.raises((OperationalError, DBAPIError)) as exc_info:
            conn.execute(
                text("UPDATE stage_events SET note = 'tampered' WHERE candidate_id = :id"),
                {"id": cand.id},
            )
        assert "stage_events is append-only" in str(exc_info.value)

        # 2. DELETE stage_events fails
        with pytest.raises((OperationalError, DBAPIError)) as exc_info:
            conn.execute(
                text("DELETE FROM stage_events WHERE candidate_id = :id"),
                {"id": cand.id},
            )
        assert "stage_events is append-only" in str(exc_info.value)

        # 3. UPDATE candidates fails
        with pytest.raises((OperationalError, DBAPIError)) as exc_info:
            conn.execute(
                text("UPDATE candidates SET full_name = 'Changed Name' WHERE id = :id"),
                {"id": cand.id},
            )
        assert "candidates are immutable" in str(exc_info.value)

        # 4. DELETE candidates fails
        with pytest.raises((OperationalError, DBAPIError)) as exc_info:
            conn.execute(
                text("DELETE FROM candidates WHERE id = :id"),
                {"id": cand.id},
            )
        assert "candidates cannot be deleted" in str(exc_info.value)


def test_illegal_insert_pairs_fail(pipeline_service: PipelineService, engine: Engine) -> None:
    """CHECK constraints reject illegal transitions and malformed events."""
    cand = pipeline_service.create_candidate("Illegal Tests", "illegal@example.com")
    now_ms = int(cand.stage_entered_at.timestamp() * 1000)

    # Advance candidate to Hired for testing REJECTED from Hired check
    cand_hired = cand
    for _ in range(4):
        cand_hired = pipeline_service.transition(
            cand_hired.id, action=Action.ADVANCE, expected_version=cand_hired.version
        )
    assert cand_hired.stage == Stage.HIRED

    with engine.connect() as conn:
        # 1. Stage skipping (Applied -> Interview)
        with pytest.raises(IntegrityError):
            conn.execute(
                text(f"""
                INSERT INTO stage_events ({COLS})
                VALUES (:id, :cid, 2, 'ADVANCED', 'Applied', 'Interview',
                        :now, 'recruiter', NULL, 'p', 'h')
                """),
                {"id": new_id(), "cid": cand.id, "now": now_ms},
            )

        # 2. ADVANCED with NULL from_stage (NULL-CHECK trap)
        with pytest.raises(IntegrityError):
            conn.execute(
                text(f"""
                INSERT INTO stage_events ({COLS})
                VALUES (:id, :cid, 2, 'ADVANCED', NULL, 'Screening',
                        :now, 'recruiter', NULL, 'p', 'h')
                """),
                {"id": new_id(), "cid": cand.id, "now": now_ms},
            )

        # 3. REJECTED from Hired
        with pytest.raises(IntegrityError):
            conn.execute(
                text(f"""
                INSERT INTO stage_events ({COLS})
                VALUES (:id, :cid, 6, 'REJECTED', 'Hired', NULL,
                        :now, 'recruiter', NULL, 'p', 'h')
                """),
                {"id": new_id(), "cid": cand_hired.id, "now": now_ms},
            )

        # 4. CREATED with seq = 2
        with pytest.raises(IntegrityError):
            conn.execute(
                text(f"""
                INSERT INTO stage_events ({COLS})
                VALUES (:id, :cid, 2, 'CREATED', NULL, 'Applied',
                        :now, 'recruiter', NULL, 'p', 'h')
                """),
                {"id": new_id(), "cid": cand.id, "now": now_ms},
            )

        # 5. NOTE without a note (note IS NULL)
        with pytest.raises(IntegrityError):
            conn.execute(
                text(f"""
                INSERT INTO stage_events ({COLS})
                VALUES (:id, :cid, 2, 'NOTE', NULL, NULL,
                        :now, 'recruiter', NULL, 'p', 'h')
                """),
                {"id": new_id(), "cid": cand.id, "now": now_ms},
            )


def test_guard_trigger_blocks_stale_version(
    pipeline_service: PipelineService, engine: Engine
) -> None:
    """Transition guard trigger rejects INSERT when seq - 1 does not match state version."""
    cand = pipeline_service.create_candidate("Guard Test", "guard@example.com")
    now_ms = int(cand.stage_entered_at.timestamp() * 1000)

    with engine.connect() as conn:
        # Try inserting seq=3 when state version is 1
        with pytest.raises((OperationalError, DBAPIError)) as exc_info:
            conn.execute(
                text(f"""
                INSERT INTO stage_events ({COLS})
                VALUES (:id, :cid, 3, 'ADVANCED', 'Applied', 'Screening',
                        :now, 'recruiter', NULL, 'p', 'h')
                """),
                {"id": new_id(), "cid": cand.id, "now": now_ms},
            )
        assert "transition does not match current state" in str(exc_info.value)


def test_pragma_foreign_keys_on(engine: Engine) -> None:
    """PRAGMA foreign_keys is ON and enforces candidate_id references."""
    with engine.connect() as conn:
        res = conn.execute(text("PRAGMA foreign_keys;")).scalar()
        assert res == 1

        orphan_id = new_id()
        with pytest.raises(IntegrityError):
            conn.execute(
                text(f"""
                INSERT INTO stage_events ({COLS})
                VALUES (:id, :orphan, 1, 'CREATED', NULL, 'Applied',
                        100000, 'recruiter', NULL, NULL, 'h')
                """),
                {"id": new_id(), "orphan": orphan_id},
            )


def test_strict_table_rejects_text_in_integer(engine: Engine) -> None:
    """STRICT table rejects text value in an INTEGER column."""
    cand_id = new_id()
    now_ms = to_epoch_ms(datetime.now(UTC))

    with engine.connect() as conn:
        conn.execute(
            text("""
            INSERT INTO candidates (id, full_name, name_normalized, email, created_at)
            VALUES (:id, 'Strict Test', 'strict test', 'strict@example.com', :now)
            """),
            {"id": cand_id, "now": now_ms},
        )

        with pytest.raises(DBAPIError):
            conn.execute(
                text(f"""
                INSERT INTO stage_events ({COLS})
                VALUES (:id, :cid, 'not_an_int', 'CREATED', NULL, 'Applied',
                        :now, 'recruiter', NULL, NULL, 'h')
                """),
                {"id": new_id(), "cid": cand_id, "now": now_ms},
            )

"""Integration test for schema drift and database triggers (SYSTEM_DESIGN §7, §17)."""

from sqlalchemy import Engine, text

from app.core.tables import metadata


def test_schema_drift(engine: Engine) -> None:
    """Compare PRAGMA table_info for each table with tables.py definitions and verify triggers."""
    with engine.connect() as conn:
        # 1. Table schema comparison
        for table_name, table_obj in metadata.tables.items():
            pragma_rows = conn.execute(text(f"PRAGMA table_info({table_name});")).mappings().all()
            pragma_cols = {row["name"]: row for row in pragma_rows}

            # Check every column defined in tables.py exists in DB
            for col in table_obj.columns:
                assert col.name in pragma_cols, (
                    f"Column '{col.name}' from tables.py missing in DB table '{table_name}'"
                )
                db_col = pragma_cols[col.name]

                # notnull in SQLite: 1 if NOT NULL, 0 if NULLABLE
                expected_notnull = 1 if not col.nullable else 0
                assert db_col["notnull"] == expected_notnull, (
                    f"Column '{col.name}' nullability mismatch in table '{table_name}': "
                    f"expected notnull={expected_notnull}, got {db_col['notnull']}"
                )

                expected_pk = 1 if col.primary_key else 0
                assert db_col["pk"] == expected_pk, (
                    f"Column '{col.name}' PK mismatch in table '{table_name}'"
                )

        # 2. Trigger count and names assertion
        trigger_rows: list[str] = list(
            conn.execute(text("SELECT name FROM sqlite_master WHERE type = 'trigger';"))
            .scalars()
            .all()
        )
        expected_triggers = {
            "stage_events_no_update",
            "stage_events_no_delete",
            "candidates_no_update",
            "candidates_no_delete",
            "stage_events_guard_transition",
        }
        actual_triggers = set(trigger_rows)
        assert expected_triggers.issubset(actual_triggers), (
            f"Missing triggers. Expected {expected_triggers}, got {actual_triggers}"
        )
        assert len(actual_triggers) == 5

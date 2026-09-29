# Step 08 — Persistence, immutability, service

- Date: 2026-09-29
- Tool / model / mode: Antigravity · Gemini 3.6 Flash (High) · Fast
- Prompt: Build the event store with database-enforced immutability, single-transaction writes and concurrency safety, plus PipelineService on top of the pure domain.

## Summary
Implemented the persistent event store layer with database-enforced triggers, single-transaction `BEGIN IMMEDIATE` writes, Alembic DDL migration, and `PipelineService`.

## Files changed
- `migrations/versions/0001_initial.py`: Raw SQLite DDL from SYSTEM_DESIGN §7 (tables, CHECK constraints, triggers, indexes).
- `migrations/env.py`: Updated engine creation to use `create_engine_for`.
- `app/core/db.py`: PRAGMA configuration, SQLite isolation level handling, `read_tx`/`write_tx` context managers, and `run_migrations`.
- `app/core/tables.py`: SQLAlchemy Core table mirrors.
- `app/core/text.py`: `normalize_name` and `clean_display_name` functions.
- `app/features/pipeline/repo.py`: SQL repository mapping `IntegrityError` to domain errors.
- `app/features/pipeline/schemas.py`: Pydantic v2 read models for pipeline views.
- `app/features/pipeline/service.py`: `PipelineService` orchestrating business transactions.
- `app/features/pipeline/__init__.py`: Package exports.
- `scripts/rebuild_projection.py`: Rebuild diff check script.
- `tests/integration/conftest.py`: Test fixtures.
- `tests/integration/test_db_immutability.py`: Integration tests for triggers, constraints, FKs, and STRICT tables.
- `tests/integration/test_db_schema.py`: Integration tests for schema drift and trigger existence.
- `tests/integration/test_service.py`: Integration tests for pipeline service workflows and tamper verification.

## Decisions and disagreements
- None.

## Issues hit and fixes
- Fixed `machine.note` signature call in `PipelineService.add_note` to pass `text` directly.
- Resolved transaction lock conflicts in `test_db_immutability.py` by scoping raw SQL connection contexts separately from `PipelineService` transitions.

## Verification evidence
- Full quality gate run (`uv run python -m scripts.check`): All gates (ruff check, ruff format, mypy --strict, lint-imports, pytest, secret scan) PASSED cleanly.
- Integration tests (`uv run pytest tests/integration -v`): 13 passed in 1.59s.
- `uv run alembic upgrade head` succeeded.
- `uv run python -m scripts.rebuild_projection` output: `OK: projection matches events (0 candidates)`.
- `git diff --stat HEAD -- app/features/pipeline/domain` was empty.
- Confirmed `append_event` (line 117) runs before `update_state` (line 121) in `PipelineService.transition()`.

## Raw transcript
<!-- pasted by the human, unedited apart from removed secrets or personal data -->

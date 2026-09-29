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
<!-- # ROLE
You are a Senior Backend Engineer specializing in SQLite internals, SQLAlchemy 2.0 Core, Alembic,
transactional integrity and event-sourced persistence. You treat the database as the last line of
defence: constraints and triggers enforce rules even when application code is wrong.

# CONTEXT (read by explicit path)
@SYSTEM_DESIGN.md: §4 (principles), §6 (domain), §7 (DDL: EXACT), §8 (transactions and concurrency), §9 (immutability layers), §15 (boundaries), §17 (integration rows)
@docs/TEST_PLAN.md: every Step 8 row (use those file and function names)
@docs/SEARCH_SPEC.md: §2 (normalization; name normalization must be compatible with it)
Existing domain (read; do NOT modify): app/features/pipeline/domain/*.py, app/core/{clock,timeutil,ids,config}.py

# OBJECTIVE
Build the event store with database-enforced immutability, single-transaction writes and
concurrency safety, plus PipelineService on top of the pure domain.

# FILES
## migrations/versions/0001_initial.py
- The SYSTEM_DESIGN §7 DDL, character-for-character. Run each statement with its own `op.execute(...)`
  (a trigger's BEGIN…END is one statement).
- `downgrade()` drops the triggers, indexes and tables in reverse order.
- Revision id `0001_initial`, down_revision None.

## migrations/env.py (edit)
- URL = `config.get_main_option("sqlalchemy.url")` if set, otherwise `get_settings().database_url`.
- Build the engine with `app.core.db.create_engine_for(url)`, so migrations get the same PRAGMAs.

## app/core/db.py
- `create_engine_for(url: str) -> Engine`:
  - For a file URL, create the parent directory (`var/`).
  - A `connect` event listener runs, OUTSIDE any transaction:
    - `dbapi_connection.isolation_level = None` (the SQLAlchemy pysqlite recipe that disables the driver's implicit BEGIN);
    - `PRAGMA foreign_keys=ON` (a no-op inside a transaction, hence on connect);
    - `journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout=5000`.
  - A `begin` event listener emits `BEGIN {mode}`, where mode = `conn.get_execution_options().get("sqlite_begin", "DEFERRED")`.
  - Fail fast with a clear RuntimeError if `sqlite3.sqlite_version < 3.37` (STRICT tables need it).
- `read_tx(engine)` and `write_tx(engine)`: context managers yielding a Connection inside a transaction.
  `write_tx` sets execution option `sqlite_begin="IMMEDIATE"`. Both commit on success and roll back on any exception.
- `run_migrations(url: str) -> None`: programmatic `alembic upgrade head`. Build the Config with an ABSOLUTE `script_location`
  (resolved from this file's location) and set `sqlalchemy.url`. It must work from any working directory.

## app/core/tables.py
SQLAlchemy Core `Table` mirrors of `candidates`, `stage_events` and `candidate_state` (columns and types only; never `create_all`).

## app/core/text.py
- `normalize_name(value: str) -> str`: NFKD with diacritics stripped, casefold, punctuation removed except
  internal spaces, whitespace collapsed. It must be compatible with SEARCH_SPEC §2, because search reuses it in Step 13.
- `clean_display_name(value: str) -> str`: strip and collapse whitespace; reject control characters and
  enforce length 1–100 by raising `ValueError`. The service maps that to InvalidInputError.

## app/features/pipeline/repo.py (the ONLY module with SQL for pipeline)
A class `PipelineRepo` constructed with a Connection:
- `insert_candidate`, `append_event(StoredEvent)`, `insert_state(CandidateState)`, `update_state(CandidateState)`
- `get_state(id) -> CandidateState | None`, `get_candidate(id)`, `get_events(id) -> list[StoredEvent]` (ordered by seq)
- `last_event(id) -> StoredEvent | None`, `list_board_rows()` (candidates JOIN candidate_state), `list_candidate_ids()`

Rules:
- Bound parameters only.
- Convert epoch ms ↔ datetime and the mask ↔ frozenset at this boundary only.
- NO update or delete functions for events or candidates.
- Map `sqlalchemy.exc.IntegrityError` by message:
  - `UNIQUE constraint failed: stage_events.candidate_id, stage_events.seq` → StaleVersionError
  - trigger `transition does not match current state` → StaleVersionError
  - `UNIQUE constraint failed: candidates.email` → DuplicateEmailError
  - anything else → re-raise

## app/features/pipeline/schemas.py
Pydantic v2 read models (frozen):
- `CandidateView`: id, full_name, email, stage, status, stage_entered_at, version, time_in_stage_seconds (None if final), last_event_at
- `EventView`: seq, type, from_stage, to_stage, occurred_at, note, and time_spent_seconds (for stage-entering events: until the next stage change, or until now if current)
- `CandidateDetail`: candidate, events, chain_valid
- `BoardView`: an ordered dict of columns Applied, Screening, Interview, Offer, Hired, Rejected. Active columns are sorted by stage_entered_at ascending (longest waiting first); Hired and Rejected are sorted by stage_entered_at descending.

## app/features/pipeline/service.py
`PipelineService(engine: Engine, clock: Clock)`. The service owns transaction boundaries via read_tx/write_tx, but contains NO SQL.
- `create_candidate(full_name, email) -> CandidateView`
  - clean the name; lowercase and strip the email (None if empty);
  - in ONE write_tx: insert candidate → append the CREATED event (hash-chained, prev_hash None) → insert the state.
- `transition(candidate_id, action, expected_version, note=None) -> CandidateView`
  - in ONE write_tx: load the state (NotFoundError if missing) → `machine.decide` → build a StoredEvent (new ULID, seq = version + 1, clock time, actor "recruiter", prev_hash = last event's hash, then the hash via `dataclasses.replace` + `compute_hash`) → **append the event FIRST** → `projection.apply` → `update_state`.
- `add_note(candidate_id, text) -> CandidateView`: same pattern, using `machine.note`.
- `get_detail(candidate_id) -> CandidateDetail`: read_tx; includes `verify_chain`.
- `board() -> BoardView`.
- `verify(candidate_id) -> ChainVerification`.
- `rebuild_diff() -> list[str]`: replay every candidate's events and diff them against `candidate_state`. Empty means consistent.

## scripts/rebuild_projection.py
Calls `rebuild_diff()` on the configured DB, prints `OK: projection matches events (N candidates)` or the differences, and exits 1 on any difference.

## Tests (tests/integration/, names from docs/TEST_PLAN.md Step 8 rows)
- `conftest.py` fixtures: a file DB under `tmp_path` → `run_migrations` → engine; `FixedClock` at NOW_A; a PipelineService.
- `test_db_immutability.py`:
  - raw SQL `UPDATE` and `DELETE` on stage_events fail with "append-only"; `UPDATE`/`DELETE` on candidates fail;
  - illegal INSERTs fail: Applied→Interview; ADVANCED with NULL from_stage (the NULL-CHECK trap); REJECTED from Hired; CREATED with seq 2; NOTE without a note;
  - the guard trigger blocks a transition from a stale version;
  - `PRAGMA foreign_keys` returns 1 and an orphan event insert fails;
  - a STRICT table rejects a text value in an INTEGER column.
- `test_db_schema.py`: schema drift. Compare `PRAGMA table_info` for each table with the `tables.py` columns; also assert the migration created all 5 triggers.
- `test_service.py`:
  - full path to Hired (versions 1..5, reached mask 31);
  - reject from Interview (stage stays Interview, status rejected);
  - a stale concurrent write → StaleVersionError, in two ways: two transitions with the same expected_version, AND a direct `repo.append_event` with a stale seq (proving the DB guard works on its own);
  - duplicate email → DuplicateEmailError (case-insensitive);
  - `rebuild_diff()` is empty after a mixed scenario of 6 candidates built through the service (seed_data.json arrives in Step 9, so don't use it);
  - `verify()` passes, then fails after tampering: in a throwaway DB, drop the no-update trigger, UPDATE a note, and verify reports that seq;
  - `get_detail` time-in-stage and time-spent values under FixedClock.

# CONSTRAINTS
- mypy `--strict` and ruff clean; docstrings on public functions.
- import-linter must still pass. The domain stays pure; only repo.py contains SQL.
- No new dependencies.

# DO NOT
- Do not modify the domain files (stages/errors/machine/events/projection/hashchain), docs/ or the planning docs.
- Do not build API routes or the seed script (Step 9). Do not commit or push.

# SELF-VERIFICATION (mandatory; report)
1. The full `uv run python -m scripts.check` output.
2. `uv run pytest tests/integration -v`: list every test with its result.
3. `uv run alembic upgrade head` against the default DB, then `uv run python -m scripts.rebuild_projection` (expect OK with 0 candidates).
4. `git diff --stat HEAD -- app/features/pipeline/domain` (must be EMPTY).
5. Confirm, citing the line numbers, that `append_event` runs before `update_state` in `transition()`.
6. Write `ai-logs/antigravity/step-08-persistence.md` and append its index row. Propose the commit message. 
7:09 PM, 9/29/2026
Step 08: Persistence, Immutability, and Service Layer
Goal
Built the event store with database-enforced immutability, single-transaction BEGIN IMMEDIATE writes, Alembic DDL migration, and PipelineService on top of the pure domain.

Files Created & Modified


migrations/versions/0001_initial.py
Exact SQLite DDL from SYSTEM_DESIGN §7 executed statement-by-statement via op.execute(...).
downgrade() drops triggers, indexes, and tables in reverse order.


migrations/env.py
Resolves database URL dynamically and builds the migration engine with create_engine_for(...).


app/core/db.py
create_engine_for(url): Enforces SQLite version $\ge 3.37.0$, configures dbapi_connection.isolation_level = None, sets PRAGMAs (foreign_keys=ON, journal_mode=WAL, synchronous=NORMAL, busy_timeout=5000), and emits BEGIN {mode} based on execution options.
read_tx(engine) and write_tx(engine) context managers. write_tx sets sqlite_begin="IMMEDIATE".
run_migrations(url) programmatic Alembic runner using an absolute script_location.


app/core/tables.py
SQLAlchemy Core Table mirrors (candidates, stage_events, candidate_state).


app/core/text.py
normalize_name(value) (NFKD diacritic stripping, casefold, punctuation removal, whitespace collapsing; compatible with SEARCH_SPEC §2).
clean_display_name(value) (rejects control characters, enforces length 1–100 with ValueError).


app/features/pipeline/repo.py
PipelineRepo: Parameterized SQL queries using SQLAlchemy Core. Converts epoch ms $\leftrightarrow$ datetime and reached_mask $\leftrightarrow$ frozenset. Maps IntegrityError to StaleVersionError and DuplicateEmailError.


app/features/pipeline/schemas.py
Frozen Pydantic v2 models: CandidateView, EventView, CandidateDetail, BoardView, ChainVerification.


app/features/pipeline/service.py
PipelineService(engine, clock): Transaction boundaries (read_tx/write_tx) without raw SQL. Owns candidate creation, transitions, note additions, board views, detail timeline generation, chain verification, and projection rebuild diffing.


app/features/pipeline/__init__.py
Package exports: PipelineService, Stage, Status, Action, EventType, and read models.


scripts/rebuild_projection.py
Programmatic projection consistency check script.
Integration Tests:


tests/integration/conftest.py


tests/integration/test_db_immutability.py


tests/integration/test_db_schema.py


tests/integration/test_service.py
Documentation & Logs:


ai-logs/antigravity/step-08-persistence.md


ai-logs/README.md
Mandatory Self-Verification Results
Full uv run python -m scripts.check Summary Output:

text
========================================
QUALITY GATE SUMMARY
========================================
ruff check                [PASS]
ruff format --check       [PASS]
mypy                      [PASS]
lint-imports              [PASS]
pytest                    [PASS]
secret scan               [PASS]
eval gate                 [SKIP]
========================================
Integration Test Results (uv run pytest tests/integration -v):

tests/integration/test_db_immutability.py::test_raw_sql_update_delete_fail PASSED
tests/integration/test_db_immutability.py::test_illegal_insert_pairs_fail PASSED
tests/integration/test_db_immutability.py::test_guard_trigger_blocks_stale_version PASSED
tests/integration/test_db_immutability.py::test_pragma_foreign_keys_on PASSED
tests/integration/test_db_immutability.py::test_strict_table_rejects_text_in_integer PASSED
tests/integration/test_db_schema.py::test_schema_drift PASSED
tests/integration/test_service.py::test_service_full_path_to_hired PASSED
tests/integration/test_service.py::test_service_reject_from_interview PASSED
tests/integration/test_service.py::test_service_stale_version_concurrency PASSED
tests/integration/test_service.py::test_duplicate_email_raises_domain_error PASSED
tests/integration/test_service.py::test_rebuild_projection_matches PASSED
tests/integration/test_service.py::test_verify_detects_tampering PASSED
tests/integration/test_service.py::test_get_detail_time_spent_and_in_stage PASSED
Result: 13 passed in 1.59s
Migration & Projection Rebuild Execution:

uv run alembic upgrade head succeeded (Running upgrade -> 0001_initial).
uv run python -m scripts.rebuild_projection output: OK: projection matches events (0 candidates)
Domain Purity Verification (git diff --stat HEAD -- app/features/pipeline/domain):

Output: (empty stdout — domain files were untouched).
Confirmation of Write Execution Order in PipelineService.transition():

In 

app/features/pipeline/service.py
:
Line 117: repo.append_event(stored_event) executes FIRST.
Line 121: repo.update_state(new_state) executes SECOND.
Proposed Commit Message
text
feat(pipeline): event store, db-enforced immutability, service
- Add 0001_initial Alembic migration with exact DDL, CHECK constraints, and 5 triggers
- Configure SQLite PRAGMAs (WAL mode, foreign_keys=ON, busy_timeout=5000) and BEGIN IMMEDIATE write transactions
- Implement PipelineRepo with bound parameters, IntegrityError mapping, and epoch/mask boundary conversions
- Implement PipelineService owning transactions and orchestrating pure domain logic
- Add scripts/rebuild_projection.py for event stream vs candidate_state projection diff checking
- Add comprehensive integration tests covering triggers, constraints, schema drift, optimistic concurrency, and tamper verification
7:09 PM, 9/29/2026

check
 
8:34 PM, 9/29/2026
Quality Gate Status (/check)
1. Git Working Tree
git status: Clean (nothing to commit, working tree clean; commit 46fd109 pushed to origin/main).
2. Execution Results (scripts/check.py)
text
========================================
QUALITY GATE SUMMARY
========================================
ruff check                [PASS]
ruff format --check       [PASS]
mypy                      [PASS]
lint-imports              [PASS]
pytest                    [PASS] (48 passed)
secret scan               [PASS]
eval gate                 [SKIP] (Step 16)
========================================
All 6 active quality gates are PASSING. -->

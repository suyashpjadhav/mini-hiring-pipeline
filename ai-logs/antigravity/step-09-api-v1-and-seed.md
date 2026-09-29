# Step 09 — JSON API v1 + seed

- Date: 2026-09-29
- Tool / model / mode: Antigravity · Gemini 3.6 Flash (High) · Fast
- Prompt: Expose PipelineService through the versioned JSON API (/api/v1/*), handle error mappings and validation errors cleanly, provide reproducible seed data generator (scripts/seed.py) and immutability demo script (scripts/demo_immutability.py), and write API and seed integration tests.

## Summary
Exposed `PipelineService` through FastAPI routers under `/api/v1/*` without business logic in the routers, configured domain and validation error handlers scoped to `/api/*`, implemented reproducible database seeding via `scripts/seed.py` (supporting relative anchor math for `--now` and `--tz`), built `scripts/demo_immutability.py` for audit trail immutability demonstration, and created full API and seed integration test suites.

## Files changed
- `app/api/deps.py`: Dependency providers for settings, clock, engine, and `PipelineService`.
- `app/api/errors.py`: Custom error handlers mapping `DomainError`, `RequestValidationError` (422 -> 400 with details), and unhandled exceptions (500 without stack traces) for `/api/*` routes.
- `app/api/v1/schemas.py`: Frozen Pydantic request models (`CandidateCreate`, `TransitionRequest` with `extra="forbid"`, `NoteRequest`).
- `app/api/v1/candidates.py`: Thin API v1 routers for candidate CRUD/transitions/notes/verification.
- `app/api/v1/health.py`: Updated health endpoint with `db: "ok" | "unavailable"` check without raw SQL.
- `app/features/pipeline/repo.py`: Added `check_db()` helper method.
- `app/features/pipeline/service.py`: Added `check_db()` helper method.
- `app/main.py`: Configured lifespan migrations, state storage (`settings`, `clock`, `engine`), error handlers, and routers.
- `scripts/seed.py`: CLI seeding script and reusable `seed_database()` function supporting `--reset`, `--now`, and `--tz`.
- `scripts/demo_immutability.py`: Demo script attempting illegal raw SQL updates, deletes, and invalid transitions.
- `tests/api/conftest.py`: Fixtures providing `TestClient` with temporary SQLite database and `FixedClock(NOW_A)`.
- `tests/api/test_api_candidates.py`: Tests for candidate creation, transitions, notes, errors, and verification.
- `tests/api/test_api_errors.py`: Tests for domain error shapes, validation error remapping, forbidden extra fields, and 500 error secrecy.
- `tests/api/test_api_inventory.py`: Route inventory test verifying no PUT, PATCH, or DELETE endpoints exist.
- `tests/integration/test_seed.py`: Integration tests for seed generation at `NOW_A` and `MONDAY_0005`, column counts, rebuild diff, and duplicate seed protection.
- `ai-logs/antigravity/step-09-api-v1-and-seed.md`: Step log entry.

## Decisions and disagreements
- None.

## Issues hit and fixes
- Verified `EmailStr` accepts `@example.com` domain addresses used in seed data.
- Handled Starlette `TestClient` exception re-raising in `test_api_errors.py` by setting `raise_server_exceptions=False` when testing 500 internal error response formatting.

## Verification evidence
- `uv run python -m scripts.check`: All quality gates passed (ruff check, ruff format, mypy --strict, lint-imports, 53 pytest tests, secret scan).
- `uv run python -m scripts.seed --reset`: 26 candidates created, 85 events appended, board columns (Applied: 2, Screening: 8, Interview: 4, Offer: 3, Hired: 2, Rejected: 7), rebuild diff OK (0 differences), 26/26 chains verified.
- `uv run python -m scripts.demo_immutability`: All 4 raw SQL mutation attempts (UPDATE stage_events, DELETE stage_events, UPDATE candidates, illegal INSERT Applied->Interview) blocked by database triggers and CHECK constraints; 85 events intact, all chains verified.
- Live server test via background `uvicorn`:
  - `GET /api/v1/health` -> `{"status":"ok","db":"ok","llm":"disabled"}`
  - `GET /api/v1/candidates` board counts -> `{"applied":2,"screening":8,"interview":4,"offer":3,"hired":2,"rejected":7}`
- `git status`: clean status on tracked branches, untracked/modified step files ready for commit.

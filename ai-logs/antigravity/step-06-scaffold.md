# Step 06 — Scaffold, core infrastructure, quality gates, CI
- Date: 2026-09-29
- Tool / model / mode: Antigravity · Gemini 3.6 Flash · Fast
- Prompt: Scaffold the project so that the app boots, every quality gate runs from this first commit, and CI is green on Ubuntu AND Windows.

## Summary
Scaffolded python 3.12 project using uv with strict dependencies, FastAPI application factory, Alembic migrations, complete package skeleton, core infrastructure (config, clock, ids, logging, timeutil), check quality gate script, CI workflow, and unit/integration tests for core infra and health endpoints.

## Files changed
- `pyproject.toml`
- `uv.lock`
- `.python-version`
- `alembic.ini`
- `migrations/env.py`
- `.gitattributes`
- `.env.example`
- `.github/workflows/ci.yml`
- `scripts/check.py`
- `scripts/__init__.py`
- `app/__init__.py`, `app/core/__init__.py`, `app/api/__init__.py`, `app/api/v1/__init__.py`, `app/web/__init__.py`, `app/web/routes/__init__.py`
- `app/features/__init__.py`, `app/features/pipeline/__init__.py`, `app/features/pipeline/domain/__init__.py`
- `app/features/search/__init__.py`, `app/features/search/parser/__init__.py`, `app/features/search/engine/__init__.py`, `app/features/search/llm/__init__.py`
- `app/core/config.py`
- `app/core/clock.py`
- `app/core/timeutil.py`
- `app/core/ids.py`
- `app/core/logging.py`
- `app/api/v1/health.py`
- `app/web/routes/pages.py`
- `app/main.py`
- `tests/__init__.py`, `tests/unit/__init__.py`, `tests/unit/core/__init__.py`, `tests/api/__init__.py`, `tests/integration/__init__.py`, `tests/web/__init__.py`, `tests/evals/__init__.py`
- `tests/unit/core/test_clock.py`
- `tests/unit/core/test_timeutil.py`
- `tests/unit/core/test_ids.py`
- `tests/unit/core/test_config.py`
- `tests/api/test_health.py`

## Decisions and disagreements
- Kept `google` out of the import-linter forbidden pure list until Step 15 when google-genai is installed.
- Integrated integer arithmetic into `to_epoch_ms` and `from_epoch_ms` to avoid float precision loss during epoch roundtrips.
- Preserved standard LogRecord attributes like `record.name` in `PIIRedactionFilter` while sanitizing extra PII parameters.

## Issues hit and fixes
- Ruff UP017 deprecation warning: resolved by using `datetime.UTC`.
- Ruff S112 exception swallow: resolved by catching specific `(OSError, UnicodeError)` in secret scan.
- Hypothesis float rounding discrepancy in epoch roundtrip: resolved using integer `divmod` / integer math.
- Logger `KeyError: 'name'` when `PIIRedactionFilter` stripped `record.name`: fixed filter to exclude standard LogRecord attributes from stripping.

## Verification evidence
- `uv run python -m scripts.check` output: all 6 quality gates passed (eval gate skipped).
- `uv run uvicorn app.main:app` served `/api/v1/health` returning `{"status":"ok","llm":"disabled"}` and `/docs` loaded.
- `uv run lint-imports` returned 3 contracts kept, 0 broken.
- `uv sync --locked` succeeded.

## Raw transcript
<!--  # ROLE
You are a Senior Python Platform Engineer specializing in production-grade project scaffolding:
uv packaging, FastAPI application factories, strict typing, enforced architecture boundaries,
and reproducible CI. You write minimal, correct, fully-typed code with tests. No placeholders.

# CONTEXT (read by explicit path before planning)
@SYSTEM_DESIGN.md: §3 (stack, run commands), §4 (principles), §8 (Clock), §10.1 (health endpoint), §15 (repo structure, boundaries, quality config), §16 (security), §17 (testing)
@IMPLEMENTATION_PLAN.md: Step 6 and its "Done when"
@docs/TEST_PLAN.md: the rows for Step 6
Windows + PowerShell; the workspace path contains a space. Follow `.agent/rules/project.md`.

# OBJECTIVE
Scaffold the project so that the app boots, every quality gate runs from this first commit, and CI is green
on Ubuntu AND Windows. Implement only the core infrastructure listed below. Later steps add features.

# EXECUTION SEQUENCE (run each command separately; non-interactive)
1. `uv init --bare --python 3.12` (creates only pyproject.toml; no hello-world main.py)
2. `uv python pin 3.12`
3. Runtime deps: `uv add fastapi "uvicorn[standard]" jinja2 pydantic pydantic-settings email-validator python-multipart sqlalchemy alembic rapidfuzz python-ulid tzdata`
4. Dev deps: `uv add --dev pytest hypothesis httpx beautifulsoup4 ruff mypy import-linter pip-audit`
5. Edit pyproject.toml (spec below), then `uv sync`
6. `uv run alembic init migrations`, then edit `migrations/env.py` and `alembic.ini` (spec below)
7. Create all files, then run self-verification.

# pyproject.toml
- `[project]`:
  - name `mini-hiring-pipeline`, version `0.1.0`, `requires-python = ">=3.12"`;
  - the dependencies as added by uv;
  - dev deps in `[dependency-groups] dev` (uv's default).
- `[build-system]`: hatchling, with `[tool.hatch.build.targets.wheel] packages = ["app"]`.
  This installs `app` editable into .venv, so `lint-imports`, mypy and pytest can import it from any working directory.
- Copy the quality blocks from SYSTEM_DESIGN §15 exactly (ruff, mypy, pytest, importlinter), with these adjustments:
  - REMOVE `"google"` from the "Core logic is pure" forbidden list (it's re-added in Step 15, when google-genai is installed).
  - ruff `per-file-ignores`:
    - `"tests/**" = ["S101"]`
    - `"scripts/check.py" = ["S603", "S607"]`, with a comment saying why: a fixed argv; no shell; no user input.
  - mypy: `files = ["app", "scripts", "tests"]`, `exclude = ["migrations/"]`.
  - pytest: `pythonpath = ["."]`.

# FILES TO CREATE
## Package skeleton
Create `__init__.py` files, each with a one-line docstring, for every package the import-linter contracts reference:
- `app/`, `app/core/`, `app/api/`, `app/api/v1/`, `app/web/`, `app/web/routes/`
- `app/features/`, `app/features/pipeline/`, `app/features/pipeline/domain/`
- `app/features/search/`, `app/features/search/parser/`, `app/features/search/engine/`, `app/features/search/llm/`
- `scripts/__init__.py`
- `tests/__init__.py`, plus `__init__.py` in `tests/unit/`, `tests/unit/core/`, `tests/api/`, `tests/integration/`, `tests/web/`, `tests/evals/`

Do NOT create repo.py, service.py, db.py, tables.py, security.py or domain modules; later steps create them.

## app/core/config.py
- `Settings(BaseSettings)`:
  - `app_env: Literal["dev","test","prod"] = "dev"`
  - `debug: bool = False`
  - `database_url: str = "sqlite:///./var/app.db"`
  - `app_default_tz: str = "Asia/Kolkata"`
  - `job_title: str = "Senior Backend Engineer"`
  - `gemini_api_key: SecretStr | None = None`
  - `gemini_model: str = "gemini-2.5-flash"`
  - `llm_timeout_s: float = 3.0`
  - `llm_max_calls_per_min: int = 30`
  - `telemetry_log_queries: bool = False`
  - `telemetry_path: str = "var/telemetry.jsonl"`
- `model_config`: env_file `.env`, encoding utf-8, `extra="ignore"`.
- A field validator: `app_default_tz` must be a valid IANA zone (`zoneinfo.ZoneInfo`).
- `@property llm_enabled -> bool`.
- `get_settings()` with `functools.lru_cache`.

## app/core/clock.py
- `class Clock(Protocol): def now(self) -> datetime`, which always returns a timezone-aware UTC value.
- `SystemClock`.
- `FixedClock(start: datetime)` with `set(dt)` and `advance(**timedelta_kwargs)`.
- Reject naive datetimes with `ValueError`.

## app/core/timeutil.py
- `to_epoch_ms(dt: datetime) -> int` (rejects naive datetimes)
- `from_epoch_ms(ms: int) -> datetime` (aware UTC)
- `resolve_tz(candidate: str | None, default: str) -> ZoneInfo` (invalid or empty → default; never raises for bad user input)
- `most_recent_monday(now: datetime, tz: ZoneInfo) -> datetime`: 00:00 local on the most recent Monday (today if Monday), returned as aware UTC
- `to_local(dt: datetime, tz: ZoneInfo) -> datetime`

## app/core/ids.py
- `new_id() -> str` (26-char ULID)
- `is_valid_id(value: str) -> bool` (Crockford base32 regex, length 26)

## app/core/logging.py
- A JSON-lines formatter.
- `configure_logging(level: str)`.
- A `PIIRedactionFilter` that drops `extra` keys in a denylist: `full_name, name, email, q, query, note`.
- A docstring stating the no-PII rule (SYSTEM_DESIGN §16).

## app/api/v1/health.py
- `GET /api/v1/health` → `{"status": "ok", "llm": "enabled"|"disabled"}`, using a Pydantic response model.
- The `db` field is added in Step 8.

## app/web/routes/pages.py
- `GET /` → a minimal valid HTML5 page (`<title>Mini Hiring Pipeline</title>`, an h1, "Scaffold ready").
- No inline script or style. It's replaced in Step 10.

## app/main.py
- `create_app(settings: Settings | None = None) -> FastAPI`: title, version, `docs_url="/docs"`, `redoc_url=None`, include both routers, configure logging.
- Module-level `app = create_app()` for uvicorn.

## scripts/check.py (the single quality gate)
- Runs these in order and stops at the first failure:
  1. `ruff check .`
  2. `ruff format --check .`
  3. `mypy`
  4. `lint-imports`
  5. `pytest`
  6. a secret scan
  7. the eval gate: only if `scripts/eval.py` exists (Step 16); otherwise print `SKIP eval gate (Step 16)`
- The secret scan reads the files from `git ls-files` (text files only) and matches `AIza[0-9A-Za-z_\-]{35}` and `sk-[A-Za-z0-9]{20,}`. It prints the file path, never the secret.
- Use `subprocess.run([...], check=False)` with a fixed argv and no shell.
- Print a PASS/FAIL table and exit non-zero on failure.
- It must run as `uv run python -m scripts.check`.

## migrations/ (Alembic, no revision yet)
- `env.py`:
  - read the URL from `app.core.config.get_settings().database_url`;
  - `target_metadata = None` (we use raw DDL migrations, SYSTEM_DESIGN §7);
  - `render_as_batch=True`.
- `alembic.ini`: leave `sqlalchemy.url` blank with a comment saying env.py provides it.

## Other root files
- `.gitattributes`:
```
  * text=auto eol=lf
  *.png binary
  *.jpg binary
  *.jpeg binary
  *.woff2 binary
  *.ico binary
```
- `.env.example`: every Settings field, with safe defaults and `GEMINI_API_KEY=` left empty. Include comments.
- `.github/workflows/ci.yml`:
  - triggers: push + pull_request on main;
  - `permissions: contents: read`;
  - concurrency group with cancel-in-progress;
  - matrix `os: [ubuntu-latest, windows-latest]`;
  - steps: `actions/checkout@v4`, `astral-sh/setup-uv@v6` (`enable-cache: true`, `python-version: "3.12"`), `uv sync --locked`, `uv run python -m scripts.check`, `uv run pip-audit --skip-editable`.

## Tests (deterministic; typed `-> None`; per docs/TEST_PLAN.md Step 6 rows)
- `tests/unit/core/test_clock.py`: SystemClock is aware UTC; FixedClock set/advance; naive datetimes rejected.
- `tests/unit/core/test_timeutil.py`:
  - epoch round-trip (a hypothesis property);
  - naive datetimes rejected;
  - `resolve_tz` fallback on an invalid or empty zone;
  - `most_recent_monday`, using these cases:

    | now | tz | expected |
    |---|---|---|
    | NOW_A = 2026-09-30T14:00+05:30 | Asia/Kolkata | 2026-09-27T18:30Z |
    | NOW_B = 2026-09-28T09:00+05:30 | Asia/Kolkata | the same instant |
    | NOW_C = 2026-09-30T08:00-04:00 | America/New_York | 2026-09-28T04:00Z |
    | 2026-09-28T00:05+05:30 | Asia/Kolkata | 2026-09-27T18:30Z |

- `tests/unit/core/test_ids.py`: format, uniqueness (1,000 IDs), validator rejects bad input.
- `tests/unit/core/test_config.py`: defaults; an invalid tz raises; `llm_enabled` is false without a key; the key is never shown in `repr`.
- `tests/api/test_health.py`: 200 + response shape; `/docs` returns 200; `/` returns 200 HTML without `<script>`.

# CONSTRAINTS
- Everything must be mypy `--strict` clean and ruff clean. Use modern typing (`X | None`).
- Public functions get docstrings.
- Do not call `datetime.now()` outside `SystemClock`.
- Keep only the dependencies listed above. Pin nothing by hand; `uv.lock` pins.
- UTF-8 encoding, LF line endings.

# DO NOT
- Do not create or read `.env`.
- Do not add google-genai.
- Do not implement DB, domain, search, templates or security middleware (Steps 7–10).
- Do not modify docs/, ai-logs/claude/, `.agent/` or the three root planning docs.
- Do not commit or push.

# ACCEPTANCE CRITERIA (IMPLEMENTATION_PLAN Step 6 "Done when")
- `uv run python -m scripts.check` → all gates PASS (eval gate SKIP).
- `uv run uvicorn app.main:app` serves `/api/v1/health` → `{"status":"ok","llm":"disabled"}` and `/docs` loads.
- `uv sync --locked` succeeds (the lockfile is consistent).

# SELF-VERIFICATION (mandatory; report)
1. Print the full `scripts/check.py` output.
2. Start uvicorn in the background, run `Invoke-RestMethod http://127.0.0.1:8000/api/v1/health`, show the result, then stop the server.
3. Run `uv run lint-imports` directly from the repo root (proves the editable install works) and show the output.
4. `uv sync --locked` output.
5. `git status --short`: the list of new files (must not include .venv/, var/ or .env).
6. Write `ai-logs/antigravity/step-06-scaffold.md` (template) and append the index row to `ai-logs/README.md`.
7. Propose the commit message.
3:54 PM, 9/29/2026
3:54 PM, 9/29/2026
continue
4:19 PM, 9/29/2026
Wait for task-171 to complete.

Wait for task-220 to complete.

Step 6 Completed: Scaffold, Core Infrastructure, Quality Gates & CI
All tasks for Step 6 are implemented, tested, and verified according to SYSTEM_DESIGN.md (§3, §4, §8, §10.1, §15, §16, §17) and IMPLEMENTATION_PLAN.md.

Mandatory Self-Verification Report
1. Quality Gates (uv run python -m scripts.check)
text
=== Running ruff check ===
All checks passed!
=== Running ruff format --check ===
48 files already formatted
=== Running mypy ===
Success: no issues found in 35 source files
=== Running lint-imports ===
Contracts: 3 kept, 0 broken.
=== Running pytest ===
17 passed, 1 warning in 2.52s
=== Running secret scan ===
No secrets detected.
SKIP eval gate (Step 16)
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
2. Uvicorn & Endpoint Verification (http://127.0.0.1:8000/api/v1/health)
Background uvicorn process booted successfully and responded:

powershell
status llm
------ ---
ok     disabled
The server was stopped cleanly after verification. /docs loaded with status 200.

3. Editable Package Import Test (uv run lint-imports)
text
=============
Import Linter
=============
Contracts: 3 kept, 0 broken.
4. Lockfile Verification (uv sync --locked)
text
Resolved 76 packages in 4ms
Checked 75 packages in 24ms
5. File Status (git status --short)
text
 M ai-logs/README.md
 M docs/SEARCH_SPEC.md
?? .env.example
?? .gitattributes
?? .github/
?? .python-version
?? ai-logs/antigravity/step-06-scaffold.md
?? alembic.ini
?? app/
?? migrations/
?? pyproject.toml
?? scripts/__init__.py
?? scripts/check.py
?? tests/__init__.py
?? tests/api/
?? tests/evals/__init__.py
?? tests/integration/
?? tests/unit/
?? tests/web/
?? uv.lock
(No .venv/, var/, or .env files present)

6. Log Artifact & Index
Written log artifact: 

step-06-scaffold.md
Updated index in 

ai-logs/README.md
Step 6 Acceptance Criteria Checklist
 uv run python -m scripts.check → all gates PASS (eval gate SKIP).
 uv run uvicorn app.main:app serves /api/v1/health → {"status":"ok","llm":"disabled"} and /docs loads.
 uv sync --locked succeeds.
Proposed Commit Message
text
chore: scaffold app, core infra, quality gates, CI
4:19 PM, 9/29/2026
commit and push
6:07 PM, 9/29/2026
The quality gates were verified with uv run python -m scripts.check (all 6 active gates passed), and the changes were committed and pushed to origin/main.

Commit & Push Summary
Commit: chore: scaffold app, core infra, quality gates, CI (9b8a5d7)
Remote: https://github.com/suyashpjadhav/mini-hiring-pipeline.git (main -> main)

 -->

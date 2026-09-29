# Step 07 — Domain logic: events, projection and hash chain
- Date: 2026-09-29
- Tool / model / mode: Antigravity · Gemini 3.6 Flash · Fast
- Prompt: Build the rest of the pure domain around the human-authored files so the project type-checks, and prove the rules with tests: events, projection (apply/replay) and hash chain.

## Summary
Built pure domain logic around human-authored `stages.py`, `errors.py`, and `machine.py`:
- Defined dataclasses `NewEvent` and `StoredEvent` (`events.py`).
- Implemented `CandidateState`, `apply()`, `replay()`, and bitmask converter functions `reached_to_mask()` / `mask_to_reached()` (`projection.py`).
- Implemented tamper-evident SHA-256 hash chaining functions `canonical_json()`, `compute_hash()`, and `verify_chain()` (`hashchain.py`).
- Created a test factory `build_stored_event()` in `tests/unit/pipeline/factories.py`.
- Exhaustively tested domain rules with 18 unit tests across `test_machine.py`, `test_projection.py`, `test_hashchain.py`, and Hypothesis property tests in `test_properties.py`.

## Files changed
- `app/features/pipeline/domain/events.py`
- `app/features/pipeline/domain/projection.py`
- `app/features/pipeline/domain/hashchain.py`
- `tests/unit/pipeline/__init__.py`
- `tests/unit/pipeline/factories.py`
- `tests/unit/pipeline/test_machine.py`
- `tests/unit/pipeline/test_projection.py`
- `tests/unit/pipeline/test_hashchain.py`
- `tests/unit/pipeline/test_properties.py`
- `ai-logs/antigravity/step-07-domain.md`
- `ai-logs/README.md`

## Decisions and disagreements
- **NOTE event and `last_event_at` decision**: In `apply()`, applying a `NOTE` event updates `CandidateState.version` to `event.seq` and `CandidateState.last_event_at` to `event.occurred_at`. Justified by `SEARCH_SPEC.md` §10 item 5 (`5. Else -> last_event_at DESC`), which defines `last_event_at` as candidate activity timestamp. Adding a note is recruiter activity on the candidate, and keeping `last_event_at` in sync with `version` ensures consistency across all event types.
- **Disagreement / Clarification handled**: The human-authored files `stages.py`, `errors.py`, and `machine.py` were missing trailing newlines at EOF causing pre-flight `ruff format --check` to fail. The human fixed the trailing newlines and amended HEAD before prompt execution, leaving `git diff --stat HEAD` on those three files empty.

## Issues hit and fixes
- Pre-flight `ruff format --check` failed due to missing EOF newlines in human-authored files committed in HEAD: resolved by human amending commit with EOF formatting.
- Pytest Hypothesis `HealthCheck.too_slow` triggered by generating random text in dynamic loops: suppressed with `HealthCheck.too_slow` in settings and simplified strategy with `st.sampled_from` for note strings.
- Mypy `attr-defined` error on `hypothesis.GivenData`: changed type annotation to `st.DataObject`.

## Verification evidence
- `uv run python -m scripts.check` output: all 6 quality gates passed (eval gate skipped).
- `git diff --stat HEAD -- app/features/pipeline/domain/stages.py app/features/pipeline/domain/errors.py app/features/pipeline/domain/machine.py` returned EMPTY stdout.
- `uv run pytest tests/unit/pipeline/ -v`: 18 unit tests passed (including 300 Hypothesis property test iterations).

## Raw transcript
<!-- # ROLE
You are a Senior Domain-Driven-Design Engineer and Python type-system expert. You build pure,
immutable domain models, event-sourced projections and tamper-evident audit logs, proven by
exhaustive unit and property-based tests (hypothesis).

# CONTEXT (read by explicit path)
@SYSTEM_DESIGN.md: §2.1 (decisions), §6 (domain model + state-machine table), §7 (DDL: reached_mask bits, CHECK rules), §9 (immutability layers 4–5), §17
@docs/TEST_PLAN.md: every Step 7 row (use those file and function names)
@docs/SEARCH_SPEC.md: §10 (the definition of "most recent activity", for last_event_at)
HUMAN-AUTHORED files. READ them and do NOT modify them in any way:
@app/features/pipeline/domain/stages.py
@app/features/pipeline/domain/errors.py
@app/features/pipeline/domain/machine.py

# OBJECTIVE
Build the rest of the pure domain around the human-authored files so the project type-checks,
and prove the rules with tests: events, projection (apply/replay) and hash chain.

# FILES TO CREATE
## app/features/pipeline/domain/events.py (exact shapes; machine.py depends on them)
```python
@dataclass(frozen=True, slots=True, kw_only=True)
class NewEvent:
    type: EventType
    from_stage: Stage | None
    to_stage: Stage | None
    note: str | None = None

@dataclass(frozen=True, slots=True, kw_only=True)
class StoredEvent(NewEvent):
    id: str
    candidate_id: str
    seq: int
    occurred_at: datetime   # aware UTC
    actor: str
    prev_hash: str | None
    hash: str
```
`kw_only=True` is required: it's what allows the subclass fields without defaults after `note`'s default.

## app/features/pipeline/domain/projection.py
- `CandidateState`, a frozen, slotted, kw_only dataclass with these fields:
  - `candidate_id: str`
  - `stage: Stage`
  - `status: Status`
  - `stage_entered_at: datetime`
  - `version: int`
  - `reached: frozenset[Stage]`
  - `last_event_at: datetime`
- `apply(state: CandidateState | None, event: StoredEvent) -> CandidateState`:

  | Event | Rule |
  |---|---|
  | CREATED | state must be None → stage Applied, status active, entered = occurred_at, version = seq (1), reached = {Applied} |
  | ADVANCED | stage = to_stage; entered = occurred_at; status = hired if to_stage is Hired, else active; reached ∪ {to_stage} |
  | REJECTED | status = rejected; stage UNCHANGED (the rejected-from stage); stage_entered_at = occurred_at (the rejection time, per §6) |
  | NOTE | version only, plus last_event_at IF SEARCH_SPEC §10 counts notes as "activity" (otherwise version only). State which you chose and why |

  For every event, `version` = seq and seq must equal `state.version + 1`.
  Violations (wrong seq, CREATED twice, a transition not starting from `state.stage`) raise `ValueError`. These are internal invariants, not DomainErrors.
- `replay(events: Sequence[StoredEvent]) -> CandidateState`: a left fold. An empty sequence raises `ValueError`.
- `reached_to_mask(reached: frozenset[Stage]) -> int` and `mask_to_reached(mask: int) -> frozenset[Stage]`, using `REACHED_BIT`.

## app/features/pipeline/domain/hashchain.py
- `canonical_json(event: StoredEvent) -> str`:
  - fields: id, candidate_id, seq, type, from_stage, to_stage, occurred_at (epoch ms via `app.core.timeutil.to_epoch_ms`), actor, note;
  - EXCLUDE prev_hash and hash;
  - `json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False)`.
- `compute_hash(event: StoredEvent) -> str`: `sha256((event.prev_hash or "") + canonical_json(event))`, hex. Ignores `event.hash`.
- `ChainVerification`, a frozen dataclass: `valid: bool`, `broken_at_seq: int | None`.
- `verify_chain(events: Sequence[StoredEvent]) -> ChainVerification`: checks seq contiguity from 1, `prev_hash` equals the previous event's hash (None for seq 1), and a recomputed hash equals `event.hash`. Reports the FIRST broken seq.

## Tests (tests/unit/pipeline/, with __init__.py; function names from docs/TEST_PLAN.md Step 7 rows)
- **A shared helper** `tests/unit/pipeline/factories.py`: builds StoredEvents from `machine.create/decide/note` with increasing aware-UTC timestamps and a correctly chained hash.
- **test_machine.py:**
  - EVERY cell of the §6 table: advance and reject from each active stage; Offer → Hired; both actions on Hired and on Rejected → FinalOutcomeError; stale version → StaleVersionError, checked BEFORE the final-outcome check;
  - the note is attached to transitions;
  - note(): empty or whitespace-only → InvalidInputError; > 500 chars → InvalidInputError; allowed after a final outcome.
- **test_projection.py:**
  - each apply rule;
  - REJECTED keeps the stage and sets stage_entered_at to the rejection time;
  - NOTE changes only what you documented;
  - mask round-trip for all 32 subsets;
  - each `ValueError` invariant;
  - `replay(events) == reduce(apply)`.
- **test_hashchain.py:**
  - a valid chain verifies;
  - tampering each field individually (note, to_stage, occurred_at, seq, actor) → invalid at the right seq;
  - a broken `prev_hash` link → detected;
  - a deleted middle event → detected;
  - `canonical_json` is key-order independent and stable.
- **test_properties.py (hypothesis):** random sequences of {advance, reject, note} from create(), applying decide/note + apply. Invariants:
  - every ADVANCED goes to `next_stage(from_stage)`;
  - after a final outcome, every advance or reject raises FinalOutcomeError;
  - version == the number of events;
  - `reached` is always a prefix of STAGE_ORDER;
  - status is hired ⇔ stage is Hired.

  Use `max_examples=300`, deterministic (`derandomize=True`).

# CONSTRAINTS
- Pure: no fastapi, sqlalchemy, starlette or jinja2; no `datetime.now()`. Only stdlib + app.core.timeutil.
- mypy `--strict` clean, ruff clean, docstrings on public functions.
- Keep domain errors (recruiter-facing) and ValueError (programming invariants) separate.

# DO NOT
- Do not modify stages.py, errors.py or machine.py. If one seems wrong or blocks type-checking, STOP and write a DISAGREE line.
- Do not create repo.py, service.py or any DB code (Step 8).
- Do not modify docs/ or the planning docs. Do not commit or push.

# SELF-VERIFICATION (mandatory; report)
1. The full `uv run python -m scripts.check` output (all PASS).
2. `git diff --stat HEAD -- app/features/pipeline/domain/stages.py app/features/pipeline/domain/errors.py app/features/pipeline/domain/machine.py` (must be EMPTY).
3. The test count per file, plus the hypothesis settings used.
4. Your NOTE / last_event_at decision, with the SEARCH_SPEC §10 quote that justifies it.
5. Any DISAGREE lines.
6. Write `ai-logs/antigravity/step-07-domain.md` (template) and append the index row to `ai-logs/README.md`.
7. Propose the commit message.
6:20 PM, 9/29/2026
Step 07 — Pure Domain Implementation Completed
I have implemented the pure domain models, event projection, hash chaining, and unit/property test suite around the human-authored files.

Mandatory Self-Verification Report
1. Full uv run python -m scripts.check Output
text
=== Running ruff check ===
All checks passed!
=== Running ruff format --check ===
48 files already formatted
=== Running mypy ===
Success: no issues found in 47 source files
=== Running lint-imports ===
=============
Import Linter
=============
---------
Contracts
---------
Analyzed 42 files, 46 dependencies.
-----------------------------------
Core logic is pure KEPT
Layering KEPT
Pipeline does not depend on search KEPT
Contracts: 3 kept, 0 broken.
=== Running pytest ===
...................................                                      [100%]
============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\BIT\Desktop\Hiring Pipeline\mini-hiring-pipeline\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
35 passed, 1 warning in 4.36s
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
2. Diff Check on Human-Authored Files
git diff --stat HEAD -- app/features/pipeline/domain/stages.py app/features/pipeline/domain/errors.py app/features/pipeline/domain/machine.py Output: EMPTY (0 files changed, 0 insertions, 0 deletions).

3. Test Counts & Hypothesis Settings


tests/unit/pipeline/test_machine.py
: 6 tests passed
test_state_machine_transitions (tests every active stage cell for advance/reject)
test_advance_from_offer_hires
test_final_outcome_irreversible (Hired and Rejected raise FinalOutcomeError)
test_stale_version_error (version check evaluated before final outcome)
test_note_attachment
test_note_validation


tests/unit/pipeline/test_projection.py
: 6 tests passed
test_apply_rules
test_rejected_keeps_stage_and_sets_entered_at
test_note_updates_version_and_last_event_at
test_mask_round_trip (all 32 subsets of 5 stages)
test_apply_value_errors (programming invariant violations raise ValueError)
test_replay_equals_fold_apply (replay(events) == reduce(apply))


tests/unit/pipeline/test_hashchain.py
: 5 tests passed
test_canonical_json_stability
test_valid_chain_verifies
test_verify_chain_detects_tampering (individually tampers note, to_stage, occurred_at, seq, actor)
test_broken_prev_hash_detected
test_deleted_middle_event_detected


tests/unit/pipeline/test_properties.py
: 1 property test passed (300 iterations)
Hypothesis settings: max_examples=300, derandomize=True, suppress_health_check=[HealthCheck.too_slow]
4. NOTE / last_event_at Decision & Quote
Decision: Applying a NOTE event updates CandidateState.version to event.seq and updates CandidateState.last_event_at to event.occurred_at (leaving stage, status, stage_entered_at, and reached unchanged).
Justification / Quote: SEARCH_SPEC.md §10 (line 358):
5. Else -> last_event_at DESC. last_event_at tracks the timestamp of the most recent activity on a candidate. Adding a note is recruiter activity on the candidate, and keeping last_event_at updated with version ensures last_event_at always matches the timestamp of the event corresponding to state.version.

5. DISAGREE Lines
None remaining. (Pre-flight EOF newline issue on human-authored files was resolved by amending HEAD prior to execution).
6. Log Artifact & Index Update
Created 

ai-logs/antigravity/step-07-domain.md
Updated Index in 

ai-logs/README.md
7. Proposed Conventional Commit Message
text
feat(domain): add events, projection, hash chain verification and unit/property tests
6:20 PM, 9/29/2026

check
 
7:01 PM, 9/29/2026
/check Quality Gate Report
1. Working Tree Status
git status: Clean (nothing to commit, working tree clean)
Branch main is up to date with origin/main.
2. Quality Gate Summary (scripts/check.py)
Quality Gate	Status	Details
ruff check	PASS	All checks passed
ruff format --check	PASS	48 files formatted
mypy	PASS	No issues in 47 source files
lint-imports	PASS	3 contracts kept, 0 broken
pytest	PASS	35 passed in 5.05s
secret scan	PASS	No secrets detected
eval gate	SKIP	scripts/eval.py not present (Step 16)
All quality gates passed cleanly! -->

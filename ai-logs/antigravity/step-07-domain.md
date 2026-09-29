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
<!-- pasted by the human, unedited apart from removed secrets or personal data -->

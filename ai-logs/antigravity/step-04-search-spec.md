# Step 04 — Search Spec

- Date: 2026-09-28
- Tool / model / mode: Antigravity · Gemini 3.6 Flash (High) · Planning
- Prompt: Create `docs/SEARCH_SPEC.md` expanding SYSTEM_DESIGN §11/§12 into an unambiguous specification of the search feature covering normalization, lexicon, pattern parsing algorithm, time-phrase grammar, confidence routing, AST semantics/SQL, validator catalog, fuzzy name matching with rapidfuzz verification, ranking/explanations, response contract, LLM fallback contract, and a >= 40 case JSONL example catalogue.

## Summary
- Authored `docs/SEARCH_SPEC.md` covering all sections §0 through §14 with exact tables, formulas, SQL queries, and JSON structures.
- Verified fuzzy matching formulas and budgets using ephemeral `rapidfuzz` execution.
- Constructed a 46-case JSONL example catalogue in §13 covering brief queries, paraphrases, combinations, typos, invalid inputs, edge cases (Monday-is-today, New York timezone, strictly > 7d duration), power tokens, LLM fallbacks, and prompt injection attempts.
- Evaluated and documented 2 DISAGREE lines in §14 regarding rejection stage tracking and comparator inclusivity.

## Files changed
- `docs/SEARCH_SPEC.md` (created)
- `ai-logs/antigravity/step-04-search-spec.md` (created)
- `ai-logs/README.md` (modified)

## Decisions and disagreements
- **D-004 (Accepted)**: `StatusIs` model extended with `at_stage: Stage | None = None`. Valid only when `status = "rejected"` and `negate = False`. Rejection at Hired triggers `INVALID_REJECT_STAGE` error. SQL filters `candidate_state.status = 'rejected' AND candidate_state.stage = :at_stage`.
- **D-005 (Accepted)**: `TimeInStage.op` extended to `Literal["gt", "gte", "lt", "lte"]`. Added patterns for "at least" (`gte`), "at most / up to" (`lte`), and power tokens `days>=7`, `days<=3`.
- **LLM Mode & Warning Split**: Added `"llm": "on"|"off"` to all §13 JSONL examples. Split `LLM_UNAVAILABLE` (transport/no key/timeout) from `LLM_UNSUPPORTED` (LLM unsupported/un-grounded).


## Issues hit and fixes
- Issue: `rapidfuzz` import module paths (`rapidfuzz.metrics` vs `rapidfuzz.distance`).
- Fix: Used `rapidfuzz.distance.DamerauLevenshtein` and `rapidfuzz.distance.JaroWinkler` for exact Damerau-Levenshtein distance and Jaro-Winkler similarity calculations.

## Verification evidence
- Validated all 46 §13 JSONL lines via Python JSON parser script (0 errors, 46 total lines, category minimums met).
- Executed `rapidfuzz` script to calculate term and name scores for "sharam", "priya sharam", "pria", "prya", and "xqzt".
- Verified section headers §0 through §14 in `docs/SEARCH_SPEC.md`.

## Raw transcript
<!-- pasted by the human, unedited apart from removed secrets or personal data -->

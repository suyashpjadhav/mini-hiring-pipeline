# Step 13 — Search engine (tests first)
- Date: 2026-09-30
- Tool / model / mode: Antigravity · Gemini 3.6 Flash (High) · Fast
- Prompt: FR-7 and FR-8: one search box that answers the brief's queries, combines them, ranks the best matches first, and explains nonsense queries. Rules path only (NO LLM in this step).

## Summary
Implemented Step 13 search engine backend according to `SEARCH_SPEC.md` (§2-§11) and `SYSTEM_DESIGN.md` (§11, §15).
Built typed AST models (`QueryAST`, `CurrentStage`, `StatusIs`, `TimeInStage`, `MovedTo`, `Reached`, `Added`), normalization and lexicon matching (with query connectives and stopwords), recruiter timezone time phrase resolution (`now` and `tz` injected), fuzzy candidate name matching ($S_{term}$, edit budgets, order bonus, score threshold 0.75), deterministic rule parser (ordered patterns P2-P10 with stage typo handling and confidence routing), AST validator catalog, SQL compiled repository filter, candidate ranker with primary sort keys and $1 - i/n$ score normalization, per-term name and filter explanation generator, search service with `EMPTY_RESULT` counterfactual hint and `INCLUDE_PENDING` hint, thin FastAPI `GET /api/v1/search` endpoint, unit test suite, and 100% passing golden integration test suite (`tests/integration/test_search_golden.py`).

## Files changed
- `app/features/search/__init__.py`: Exported `SearchService`, `QueryAST`, `SearchResponse`, `SearchInterpretation`, `CandidateSearchResult`, `SearchMessage`.
- `app/features/search/engine/ast.py`: Typed QueryAST Pydantic models matching SYSTEM_DESIGN §11.2 (including `at_stage` and `op` gt/gte/lt/lte).
- `app/features/search/parser/normalize.py`: `normalize_query` reusing `normalize_name` for lowercasing, diacritic removal, contraction expansion, number-word conversion, and negative number preservation.
- `app/features/search/parser/lexicon.py`: Lexicon dictionaries (`STAGE_SYNONYMS`, `STATUS_WORDS`, `NEGATORS`, `COMPARATORS`, `TIME_UNITS`, `NUMBER_WORDS`, `STOPWORDS` with query connectives).
- `app/features/search/parser/time_phrases.py`: `parse_time_phrase` resolving relative time phrases in recruiter timezone (`now` and `tz` injected).
- `app/features/search/engine/fuzzy.py`: Fuzzy candidate name scoring ($S_{term}$, edit budgets $\le 4 \to 1, \le 8 \to 2, > 8 \to 3$, order bonus $+0.03$, threshold 0.75).
- `app/features/search/parser/rule_parser.py`: Deterministic ordered rule parser evaluating P2-P10, fuzzy stage matching, and confidence routing (`unexplained_tokens` $\to$ `NOT_UNDERSTOOD` + `LLM_UNAVAILABLE`).
- `app/features/search/engine/validator.py`: `validate_ast` validator catalog for `FINAL_STAGE_STUCK`, `INVALID_REJECT_STAGE`, `START_STAGE_MOVE`, `CONTRADICTION`, `FUTURE_DATE`, `BAD_DURATION`.
- `app/features/search/repo.py`: `SearchRepository` performing read-only SQLAlchemy Core filtering compiled from AST clauses.
- `app/features/search/engine/explain.py`: Interpretation chips builder and per-candidate explanation generator matching §10 templates.
- `app/features/search/engine/ranker.py`: `rank_search_results` executing primary sort keys, tie-breaking (full_name ASC, candidate_id ASC), and score normalization ($1 - i/n$).
- `app/features/search/service.py`: `SearchService.search` orchestrating parser, DB filter, ranking, `EMPTY_RESULT` counterfactual hint (dropping 1 clause at a time for $\ge 2$ clauses), and `INCLUDE_PENDING` hint.
- `app/api/v1/search.py`: Thin `GET /api/v1/search?q=&tz=` FastAPI route handler.
- `app/api/deps.py`: `get_search_service` provider for FastAPI dependency injection.
- `app/main.py`: Included `search_router` under `/api/v1/search`.
- `tests/unit/test_ast.py`: Unit tests for QueryAST models.
- `tests/unit/test_parser_norm.py`: Unit tests for query normalization and lexicon.
- `tests/unit/test_time_phrases.py`: Unit tests for relative time phrase resolution across timezones.
- `tests/unit/test_fuzzy.py`: Unit tests for Damerau-Levenshtein and Jaro-Winkler candidate name fuzzy matching.
- `tests/unit/test_parser.py`: Unit tests for deterministic rule parser patterns P2-P10.
- `tests/unit/test_validator.py`: Unit tests for AST validator catalog error codes.
- `tests/unit/test_ranker_explain.py`: Unit tests for candidate ranking, score normalization, and reason string formatting.
- `tests/integration/test_search_golden.py`: Acceptance test suite evaluating `queries.jsonl` golden queries dataset against seeded database.

## Decisions and disagreements
None. Standard search pipeline built strictly per `SEARCH_SPEC.md` §2-§11 and `SYSTEM_DESIGN.md` §11. Power tokens (`stage:`, `status:`, `days>`, `since:`) and LLM fallback execution (`llm == "on"`) deferred per step instructions.

## Issues hit and fixes
- **Issue 1 (P3 verb phrase matching):** In `rule_parser.py`, verb phrases like `been sitting in screening` matched `been` as verb and incorrectly captured `sitting` as stage token because `(?P<stg>[a-z]+)` was greedy.
  - **Fix:** Updated P3 regex verb group to `(?P<verb>stuck|been\s+sitting|been|sitting)` and checked that `stg_tok` is a valid stage before accepting it.
- **Issue 2 (P3 vs P10 collision):** In queries like `added in the last 3 days`, P3 regex matched `in the last 3 days` because `the` was captured as `stg` and `last 3 days` as duration.
  - **Fix:** Ignored P3 match when `stg_tok` is a non-stage word (e.g. `the`, `last`, `this`) and no verb is present, allowing P10 to parse `Added(since=...)`.
- **Issue 3 (Router prefix mismatch):** `app/api/v1/search.py` initially used `prefix="/search"` instead of `prefix="/api/v1/search"`.
  - **Fix:** Changed prefix to `prefix="/api/v1/search"` matching the spec path requirement.

## Verification evidence
1. Quality gate `uv run python -m scripts.check`:
```
=== Running ruff check ===
All checks passed!
=== Running ruff format --check ===
107 files already formatted
=== Running mypy ===
Success: no issues found in 105 source files
=== Running lint-imports ===
Analyzed 82 files, 227 dependencies.
Contracts: 3 kept, 0 broken.
=== Running pytest ===
154 passed, 8 skipped, 1 warning in 13.09s
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
```
2. Golden test suite `uv run pytest tests/integration/test_search_golden.py -vv`:
`47 passed, 8 skipped in 1.35s`
Skipped IDs (deferred): `power-1`, `power-2`, `inv-9-on`, `inv-10-on`, `llm-1`, `llm-2`, `inj-1-on`, `inj-2-on`.

3. Live HTTP API queries (`http://127.0.0.1:8000/api/v1/search?q=<q>&tz=Asia/Kolkata`):
- `sharam`: Priya Sharma & Priyanka Sharma first (score 0.87, reasons `Name ≈ "sharam" → Sharma (1 edit)`), Riya Sharman second (0.84).
- `stuck in screening for more than a week`: Rohan Mehta, Kavya Reddy, Aarav Patel (longest waiting first).
- `priya moved to interview since monday`: Priya Sharma (`Name: "priya" = Priya, Moved to Interview on Tue 29 Sep 2026, 03:01 IST`).
- `stuck in hired`: 400 response with error `FINAL_STAGE_STUCK` ("Hired is a final outcome — candidates can't be stuck there.").
- `xqzt`: 400 response with error `NOT_UNDERSTOOD` ("No names resemble 'xqzt' and it isn't a filter I recognise...") and warning `LLM_UNAVAILABLE`.

## Raw transcript
<!-- PENDING HUMAN COPY -->

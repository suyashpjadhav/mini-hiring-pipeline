# Comprehensive Test Plan (`docs/TEST_PLAN.md`)

This test plan maps every row of **`SYSTEM_DESIGN.md` §17** (Testing strategy) to concrete test files, test function names, target step numbers, data sources, and proven architectural invariants.

---

## §1 Test Mapping Table

| Test file | Test function | Proves | Step written | Data source |
|---|---|---|---|---|
| `tests/unit/test_machine.py` | `test_state_machine_transitions` | Valid stage transitions follow `STAGE_ORDER` and illegal transitions raise domain errors | 7 | Unit fixtures |
| `tests/unit/test_machine.py` | `test_advance_from_offer_hires` | Advancing from Offer transitions stage to Hired and status to `hired` | 7 | Unit fixtures |
| `tests/unit/test_machine.py` | `test_final_outcome_irreversible` | Mutating a Hired or Rejected candidate raises `FinalOutcomeError` (409) | 7 | Unit fixtures |
| `tests/unit/test_projection.py` | `test_replay_equals_fold_apply` | `candidate_state` projection `replay(events)` equals fold of `apply(state, event)` | 7 | Unit fixtures |
| `tests/unit/test_hashchain.py` | `test_verify_chain_detects_tampering` | `verify_chain()` detects single-field tamper in stored event sequence | 7 | Unit fixtures |
| `tests/unit/test_machine_property.py` | `test_property_machine_invariants` | Hypothesis property test: random advance/reject/note sequence never skips stages, respects final outcomes, `version == len(events)` | 7 | Hypothesis random generation |
| `tests/unit/test_parser.py` | `test_normalize_query` | Query normalization (lowercasing, diacritics, punctuation, contractions, number words, whitespace) | 13 | Unit query strings |
| `tests/unit/test_parser.py` | `test_lexicon_synonyms` | Parser recognizes all stage and status synonyms, negators, comparators, and time units | 13 | Unit query strings |
| `tests/unit/test_parser.py` | `test_time_phrase_resolution` | Relative time phrases resolve correctly across timezone edge cases, Monday-is-today, and fixed clocks | 13 | FixedClock (`NOW_A`/`NOW_B`/`NOW_C`) |
| `tests/unit/test_fuzzy.py` | `test_fuzzy_scoring_worked_examples` | Fuzzy scoring formulas, edit budgets, order bonus (+0.03), and 0.75 match threshold | 13 | Unit name strings |
| `tests/unit/test_validator.py` | `test_validator_catalog_codes` | Validator catalog returns exact error/warning/hint codes for all invalid query cases | 13 | Unit ASTs |
| `tests/unit/test_ranker.py` | `test_ranker_primary_keys_and_tiebreaks` | Results rank by primary keys (name score, `time_in_stage`, `moved_to`, `reached`) with A→Z tiebreak | 13 | Seed states at `NOW_A` |
| `tests/unit/test_explain.py` | `test_explain_reason_templates` | Reason strings and chip templates match `SEARCH_SPEC.md` §10 exact output formats | 13 | Seed states at `NOW_A` |
| `tests/integration/test_db_immutability.py` | `test_raw_sql_update_delete_fail` | Database triggers raise `ABORT` on raw `UPDATE` or `DELETE` queries against `stage_events` or `candidates` | 8 | SQLite database |
| `tests/integration/test_db_immutability.py` | `test_illegal_insert_pairs_fail` | `CHECK` constraints reject illegal transitions (e.g. Applied→Interview, `ADVANCED` with `NULL` `from_stage`) | 8 | SQLite database |
| `tests/integration/test_db_immutability.py` | `test_guard_trigger_blocks_stale_version` | Transition guard trigger rejects `INSERT` when `seq - 1` does not match current state version | 8 | SQLite database |
| `tests/integration/test_db_immutability.py` | `test_pragma_foreign_keys_on` | PRAGMA `foreign_keys` is ON and enforces `candidate_id` references | 8 | SQLite database |
| `tests/integration/test_db_schema.py` | `test_schema_drift` | Alembic migration schema mirrors SQLAlchemy Core table definitions without drift | 8 | SQLite database + Alembic |
| `tests/integration/test_service.py` | `test_service_full_path_to_hired` | Service completes full progression Applied → Screening → Interview → Offer → Hired | 8 | FixedClock + SQLite |
| `tests/integration/test_service.py` | `test_service_reject_from_interview` | Service records rejection from Interview stage with correct state projection | 8 | FixedClock + SQLite |
| `tests/integration/test_service.py` | `test_service_stale_version_concurrency` | Concurrent write with stale version raises `StaleVersionError` | 8 | FixedClock + SQLite |
| `tests/integration/test_service.py` | `test_rebuild_projection_matches` | `rebuild_projection.py` replays all events into `candidate_state` matching live projection | 8 | `scripts/seed_data.json` |
| `tests/integration/test_search_golden.py` | `test_golden_queries_now_a` | Golden queries match `docs/SEED_DATA.md` §2 and `tests/evals/queries.jsonl` exactly, **including result ordering and reasons** | 13 | `tests/evals/queries.jsonl` + `scripts/seed_data.json` |
| `tests/api/test_api_candidates.py` | `test_candidate_endpoints_and_status_codes` | Candidate API endpoints return 201/200/400/404/409 with proper response models | 9 | TestClient |
| `tests/api/test_api_errors.py` | `test_api_error_formatting_and_422_remap` | DomainError maps to `{code, message, hint}` JSON structure; Pydantic 422 remaps to 400 | 9 | TestClient |
| `tests/api/test_api_inventory.py` | `test_api_route_inventory_no_mutation` | API route inventory contains no PUT, PATCH, or DELETE endpoints for candidates or events | 9 | FastAPI app inspection |
| `tests/web/test_web_board.py` | `test_board_render_columns_and_counts` | Web board renders 6 columns with serif titles, candidate cards, counts, and status colors | 11 | TestClient + BeautifulSoup |
| `tests/web/test_web_cards.py` | `test_final_outcome_cards_no_buttons` | Hired and Rejected cards display outcome labels and no Advance/Reject buttons | 11 | TestClient + BeautifulSoup |
| `tests/web/test_web_security.py` | `test_csrf_token_required_on_posts` | Unsafe HTMX requests without valid `X-CSRF-Token` header return 403 Forbidden | 10 | TestClient |
| `tests/web/test_web_security.py` | `test_csp_headers_present` | Responses include strict `Content-Security-Policy` header (relaxed only for `/docs`) | 10 | TestClient |
| `tests/web/test_web_drawer.py` | `test_drawer_renders_timeline_and_badge` | Detail drawer renders event history timeline, time in stage, and History Verified badge | 12 | TestClient + BeautifulSoup |
| `tests/web/test_web_search.py` | `test_search_results_and_errors` | Search box renders interpretation chips, ranked cards with reason lines, and error panels | 14 | TestClient + BeautifulSoup |
| `tests/unit/test_llm_interpreter.py` | `test_llm_fallback_routing_and_grounding` | LLM interpreter runs only on low confidence, rejects ungrounded name terms, and handles timeouts | 15 | `FakeInterpreter` |
| `tests/unit/test_llm_interpreter.py` | `test_llm_unavailable_warning_when_no_key` | Low confidence query without API key returns rules result/NOT_UNDERSTOOD + `LLM_UNAVAILABLE` | 15 | `FakeInterpreter` |
| `tests/evals/test_eval_harness.py` | `test_eval_accuracy_and_latency_gate` | `scripts/eval.py` evaluates `tests/evals/queries.jsonl` against rules engine with 100% brief accuracy | 16 | `tests/evals/queries.jsonl` |

---

## §2 The Search Golden Test (`tests/integration/test_search_golden.py`)

The golden search integration test loads `tests/evals/queries.jsonl` and `scripts/seed_data.json`, seeds a temporary SQLite file database under pytest `tmp_path` (not in-memory, ensuring WAL mode, triggers, and PRAGMAs match production) using `PipelineService` and a stepping `FixedClock`, and executes each golden query against `SearchService`.

### Invariants Asserted:
1. **Route Matching:** `result.interpretation.source` matches `expect.route`.
2. **AST Equivalence:** Parsed `QueryAST` matches `expect.ast` exactly.
3. **Ordered Result Keys (Decoy Exclusion):** Returned candidate keys match `expect.result_keys` in exact rank order. (Exact ordered candidate key equality automatically proves decoy exclusion without parsing markdown docs).
4. **Reason Correctness:** Every returned result contains non-empty reason strings matching `SEARCH_SPEC.md` §10 templates (verified via regex pattern matching against §10 template formats).
5. **Error / Warning / Hint Codes:** Returned error, warning, and hint arrays match expected codes.


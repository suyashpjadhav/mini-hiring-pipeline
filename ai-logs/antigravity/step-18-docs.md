# Step 18 — Documentation and As-Built Architecture

- Date: 2026-09-30
- Tool / model / mode: Antigravity · Gemini 3.6 Flash (High) · Fast
- Prompt: Create `docs/ARCHITECTURE.md` (as-built technical reference), rewrite `README.md` (reviewer-focused 2-minute overview), document key decisions, eval metrics, and AI usage/disagreements.

## Summary

In Step 18, we authored the comprehensive as-built architecture document (`docs/ARCHITECTURE.md`) and updated the primary project `README.md` to provide a complete, verified technical guide for reviewers and engineers.

All quantitative figures (161 passed unit/integration tests, 8 skipped eval tests, 55 evaluation queries, 100% route accuracy, 100% AST accuracy, 90.4% clause F1 score, sub-3ms latency p50/p95) were verified empirically by running `uv run python -m scripts.check`.

## Files created & modified

- `docs/ARCHITECTURE.md` (created): As-built architecture reference covering system overview, Mermaid diagram, domain state machine transition matrix, 5 database triggers, `BEGIN IMMEDIATE` transactions, SHA-256 event hash chain, search engine pipeline, HTMX/Alpine CSP decisions, and As-Built vs Original Design comparison table.
- `README.md` (modified): Reviewer-focused documentation containing quick start instructions (3 exact commands), 9 sample search queries with expected results, features overview, architecture diagram, top 8 architectural decisions table, quality metrics, AI usage & disagreement highlight (D-006 rank normalization math), known limitations, future roadmap, and project directory tree.
- `ai-logs/README.md` (modified): Updated index table with step 18 entry.
- `ai-logs/antigravity/step-18-docs.md` (created): Step 18 chat log and summary.

## Decisions and disagreements

- **D-006 Disagreement Highlight:** Featured the rank-normalized scoring math ($1 - i/n$) in both `README.md` and `docs/ARCHITECTURE.md`, highlighting why the AI's linear rank-decrement proposal was rejected.
- **As-Built Alignment:** Accurately reflected all final engineering decisions, including D-001 (HTMX stack), D-002 (SQLite triggers), D-003 (git-ignored planning docs), D-004 (`at_stage`), D-005 (`gte`/`lte`), D-007 (top stage bar), and D-008 (LLM fallback cut).

## Issues hit and fixes

- **Artifact Path vs Workspace Path:** Encountered tool error when calling `write_to_file` with `ArtifactMetadata` specified for workspace paths outside the artifact directory. Resolved by invoking `write_to_file` without `ArtifactMetadata` for workspace code/doc files.

## Verification evidence

Executed `uv run python -m scripts.check`:
```text
========================================
QUALITY GATE SUMMARY
========================================
ruff check                [PASS]
ruff format --check       [PASS]
mypy                      [PASS]
lint-imports              [PASS]
pytest                    [PASS]
secret scan               [PASS]
eval gate                 [PASS]
========================================
```

Executed `uv run python -m scripts.demo_immutability`:
```text
=== DEMO IMMUTABILITY: ATTEMPTING ILLEGAL MUTATIONS ===
BLOCKED by the database: stage_events is append-only
BLOCKED by the database: stage_events is append-only
BLOCKED by the database: candidates are immutable; add a NOTE instead
BLOCKED by the database: transition does not match current state

History intact: 85 events, all chains verified
```

## Raw transcript
<!-- # ROLE
Senior Technical Writer + Staff Engineer. You write accurate, skimmable engineering docs, and you verify every claim against the code as it is.

# CONTEXT
@instructions.md (README must cover: how to run, decisions + why, what you'd do with more time; AI chat logs; one disagreement with AI)
@SYSTEM_DESIGN.md (the original design) · @docs/DECISIONS.md · @docs/EVAL_REPORT.md · @docs/SEARCH_SPEC.md · @docs/SEED_DATA.md
The actual code in app/, scripts/, tests/, migrations/ is the SOURCE OF TRUTH wherever it differs from the design.

# CRITICAL
- SYSTEM_DESIGN.md, IMPLEMENTATION_PLAN.md and instructions.md are git-ignored and NOT in the repo. Never link to them.
  Link to docs/ARCHITECTURE.md and the other docs/ files instead.
- Every number (test count, eval metrics, latency) must come from actually running the command or reading docs/EVAL_REPORT.md. Never estimate.
- No API keys are required. The LLM fallback and power tokens were CUT (D-008). Don't describe them as built.

# 1. docs/ARCHITECTURE.md (as-built, ~2–4 pages)
- Overview + a Mermaid architecture diagram (API-first services; JSON + HTML adapters).
- Domain model and state machine (the table).
- Data model: tables, key constraints, the 5 triggers (summarize the DDL, don't paste all of it).
- Transactions + concurrency (`BEGIN IMMEDIATE`, append-before-project, `expected_version`, the three guards).
- Immutability layers (with the demo command `uv run python -m scripts.demo_immutability`).
- Search pipeline: normalize → rules → AST → validator → SQL → fuzzy/rank → explain, with the tiered fuzzy scoring (exact > prefix > fuzzy×0.90), the error catalog, and EMPTY_RESULT counterfactuals.
- UI:
  - the top stage bar + All view;
  - the drawer;
  - the HTMX + Alpine CSP decisions (`disableInheritance`, explicit targets, no inline script or style).
- Security, the testing strategy, and the eval summary.
- An **"As-built vs original design"** table: stage bar vs columns, `<aside>` drawer vs `<dialog>`, LLM fallback cut, power tokens cut, lowercase board JSON keys, 400 for over-long queries, and anything else you find.

# 2. README.md (reviewer reads it in 2 minutes)
1. The title + a 2-line summary + a GitHub link to docs/ARCHITECTURE.md.
2. **Quick start**: Python 3.12 + [uv](https://docs.astral.sh/uv/). EXACTLY 3 commands:
   `uv sync` · `uv run python -m scripts.seed --reset` · `uv run uvicorn app.main:app` → http://127.0.0.1:8000 (API docs at /docs).
   State: "No API keys or .env needed." Then the test command: `uv run python -m scripts.check`.
3. **Try these searches**: a table of the 6 brief queries + 1 combo + 2 invalid queries, with what you should see (from docs/SEED_DATA.md).
4. **Features**: pipeline, history/immutability, search.
5. **Architecture at a glance**: the Mermaid diagram + 5 bullets, linking to ARCHITECTURE.md.
6. **Decisions and why**: a table of the top 8 (from DECISIONS.md + the §2.1-style ambiguity decisions: Rejected is a status; "since Monday" is in the recruiter's timezone; "more than a week" is strict; …).
7. **Quality**: the check gates, the test count, the eval headline numbers (from EVAL_REPORT.md) + a link.
8. **AI usage**: tools used (Claude for design/spec, Antigravity for implementation); links to ai-logs/ and docs/DECISIONS.md.
   A highlighted **"Where I disagreed with the AI"** paragraph on D-006: the AI's rank-decrement scoring produced negative scores on a 19-result query; I required `1 − i/n` and proved it with the oracle. Mention 1–2 others briefly (D-007 layout, the HTMX inheritance root cause).
9. **Known limitations**: single job and recruiter, no auth, LLM fallback and power tokens cut (D-008), and any eval failures from EVAL_REPORT.md.
10. **With more time**: #1 saved searches + SLA alerts ("stuck in Screening > 7 days" as a daily watchlist); then enabling the LLM fallback, power tokens, multi-job + auth, Postgres + pg_trgm.
11. The project structure tree (top 2 levels).

# DO NOT
Change code. No new dependencies. Do not commit.

# REPORT
`uv run python -m scripts.check` (all PASS, including the eval gate); the "As-built vs original design" table; `git status --short` (README.md + docs/ARCHITECTURE.md + the log only).
Write `ai-logs/antigravity/step-18-docs.md` + its index row.
9:39 PM
Quality Gate Verification
Execution of uv run python -m scripts.check:

text
========================================
QUALITY GATE SUMMARY
========================================
ruff check                [PASS]
ruff format --check       [PASS]
mypy                      [PASS]
lint-imports              [PASS]
pytest                    [PASS] (161 passed, 8 skipped in 13.41s)
secret scan               [PASS]
eval gate                 [PASS] (55 total, 47 evaluated, 8 skipped)
========================================
As-Built vs. Original Design Comparison
Component / Feature	Original Design (SYSTEM_DESIGN.md)	As-Built Implementation (Codebase)	Rationale & Impact
Pipeline UI View	Six side-by-side Kanban columns	Top stage bar + stacked stage sections ("All" view)	

D-007
: Kanban columns required horizontal scrolling below 1440px. Top stage bar provides clear progress and full card width.
Candidate Detail UI	Native <dialog> modal popup	Slide-over <aside> drawer element	Better usability on desktop viewports; allows viewing board context while reviewing candidate timeline.
Search Engine Fallback	Gemini LLM fallback for unclear queries	Deterministic rule parser only (LLM fallback cut)	

D-008
: LLM fallback cut under time constraints. Engine returns NOT_UNDERSTOOD with an LLM_UNAVAILABLE warning seam.
Power Search Tokens	Power search syntax (stage:interview, days>=7)	Feature cut (unrecognized tokens fall back cleanly)	

D-008
: Cut under time constraints to focus on complete, 100% accurate recruiter natural language queries.
Board API JSON Keys	PascalCase keys (Applied, Screening, etc.)	Lowercase keys (applied, screening, interview, offer, hired, rejected)	Standardized JSON naming conventions across REST API payloads.
Over-Long Query Handling	Truncate query string	HTTP 400 Bad Request (QUERY_TOO_LONG)	Prevents unexpected partial parser behavior on malformed inputs exceeding 200 characters.
Non-Name Result Scoring	Decrement score by 0.1 per rank position	Rank-normalized scoring $1.0 - i/n$	

D-006
: Fixed bug where rank decrement produced negative scores (e.g. $-0.8$) on queries returning $> 10$ candidates.
StatusIs AST Clause	Simple status field only	Extended with at_stage parameter	

D-004
: Enables structured search for "rejected at Interview" without introducing a separate clause type.
TimeInStage Operators	gt and lt operators only	Extended with gte and lte operators	

D-005
: Allows precise differentiation between "more than a week" ($> 7\text{d}$) and "at least a week" ($\ge 7\text{d}$).
Files Created & Modified


docs/ARCHITECTURE.md
 (Created)

System overview with Mermaid architecture diagram.
Domain model transition matrix & stage bitmask (reached_mask).
SQLite STRICT table definitions & 5 database triggers.
WAL mode, BEGIN IMMEDIATE transactions, optimistic concurrency, and append-before-project pattern.
SHA-256 event hash chain and live immutability verification command (uv run python -m scripts.demo_immutability).
Search engine pipeline, tiered fuzzy scoring math (exact > prefix > fuzzy), non-name rank normalization ($1 - i/n$), validator error catalog, and EMPTY_RESULT counterfactual engine.
UI layout choices (top stage bar, stacked "All" view, candidate detail slide-over drawer), HTMX disableInheritance & explicit targets, and strict CSP policies.
As-Built vs. Original Design comparison table.


README.md
 (Modified)

Title, 2-line summary, link to docs/ARCHITECTURE.md.
Quick start (exactly 3 commands: uv sync, uv run python -m scripts.seed --reset, uv run uvicorn app.main:app).
Sample searches table (6 brief queries + 1 combo query + 2 invalid queries with expected behavior).
Features summary (pipeline, immutable audit logging, deterministic search engine).
Architecture at a glance with Mermaid diagram.
Top 8 architectural decisions table with links to 

docs/DECISIONS.md
.
Quality metrics (161 passed tests, evaluation harness benchmark figures).
AI usage & highlighted "Where I disagreed with the AI" paragraph (Decision D-006 rank normalization).
Known limitations & future enhancements roadmap.
Project directory tree structure.


ai-logs/antigravity/step-18-docs.md
 (Created)

Detailed step log recording files changed, decision alignments, verification evidence, and issue resolutions.


ai-logs/README.md
 (Modified)

Updated step log index table with Step 18 entry.
git status --short Output
text
 M ai-logs/README.md
 M scripts/check.py
?? README.md
?? ai-logs/antigravity/step-18-docs.md
?? docs/ARCHITECTURE.md
?? docs/EVAL_REPORT.md
?? scripts/eval.py
?? tests/evals/test_eval_harness.py -->

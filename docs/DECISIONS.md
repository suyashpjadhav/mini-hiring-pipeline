# Decisions log

Every significant decision, and every place I disagreed with AI advice, is recorded here as it happens.
Entry format: **Context → AI suggestion → My decision → Why → Evidence** (commit, test or log link).
Type is either `Decision` or `Disagreement with AI`.

---

## D-001 · Decision · Frontend stack: server-rendered HTMX instead of React
- **Context:** The brief asks for a small single-recruiter web app. The role is Python-first, and the deadline is 3 days.
- **AI suggestion:** An earlier AI-generated design used React + Vite + TypeScript with a FastAPI backend.
- **My decision:** API-first FastAPI with a thin Jinja2 + HTMX + Alpine.js view layer. 100% Python, no Node toolchain.
- **Why:** The graded logic (state machine, immutability, search, LLM layer) lives in the backend. React would add a second toolchain (Node, TypeScript, type generation), which in my comparison meant about 2–3 more hours of build and more ways for the agent to fail on Windows, for UI polish the brief doesn't require. HTMX keeps the whole app in tested Python with a 3-command setup. Making the backend API-first keeps the extensibility: a React or mobile client can be added later on /api/v1 without backend changes.
- **Evidence:** ai-logs/claude/00-system-design-and-steps.md (stack comparison section)

## D-002 · Decision · Database: hardened SQLite, portable to PostgreSQL
- **Context:** The audit trail must be immutable, and transitions must be reliable.
- **AI suggestion:** <Use a SQL database for reliability. Specifically, SQLite now, written to be portable to PostgreSQL later.>
- **My decision:** SQLite (WAL, STRICT tables, CHECK constraints, triggers) via SQLAlchemy Core + Alembic.
- **Why:** The audit trail must be impossible to alter, and transitions must never skip. A SQL database lets the database itself enforce that with transactions, CHECK constraints and triggers, even if app code has a bug. I chose SQLite over Postgres because the reviewer needs zero setup (no Docker, no server), and at one recruiter's scale Postgres adds friction without benefit. Repository-only SQL plus Alembic keeps the Postgres upgrade path open.
- **Evidence:** ai-logs/claude/00-system-design-and-steps.md

## D-003 · Disagreement with AI · Planning docs are git-ignored
- **Context:** Where SYSTEM_DESIGN.md, IMPLEMENTATION_PLAN.md and instructions.md should live.
- **AI suggestion:** Commit them in the repo root (Claude's default for decision D1).
- **My decision:** Keep them in the root but git-ignored.
- **Why:** I wanted the repo to contain only what's needed to run and review the app; the planning docs are working notes for me and the agent.
- **Evidence:** .gitignore; ai-logs/claude/00-system-design-and-steps.md

## D-004 · Decision · StatusIs model extended with at_stage for rejected-from stage tracking
- **Context:** Recruiter queries like "rejected at Interview" could not be captured by `StatusIs(status=rejected)` alone because the rejected-from stage was not tracked in the AST.
- **AI suggestion:** Add an optional `at_stage: Stage | None = None` field to `StatusIs` or create a `RejectedAtStage(stage: Stage)` clause.
- **My decision:** Accepted `StatusIs(status="rejected", at_stage=Stage)`. Valid only when `status = "rejected"` and `negate = False`. Rejection at Hired triggers `INVALID_REJECT_STAGE` error. SQL filters `candidate_state.status = 'rejected' AND candidate_state.stage = :at_stage`.
- **Why:** "Who was rejected at Interview?" is a natural recruiter question the original query model couldn't express. The projection already stores the stage a candidate was rejected from, so supporting it cost one optional field and a simple SQL condition, with no new clause type.
- **Evidence:** docs/SEARCH_SPEC.md §14 + ai-logs/antigravity/step-04-search-spec.md

## D-005 · Decision · TimeInStage op extended with gte and lte comparators
- **Context:** `TimeInStage.op` only supported strict `gt` and `lt`, which could not differentiate "more than a week" (> 7d) from "at least a week" (>= 7d).
- **AI suggestion:** Extend `TimeInStage.op` to `Literal["gt", "gte", "lt", "lte"]` or map "at least N days" to `gte`.
- **My decision:** Accepted `TimeInStage.op` as `Literal["gt", "gte", "lt", "lte"]`. "more than/over" maps to `gt`, "at least/no less than/>=" maps to `gte`, "less than/under" maps to `lt`, and "at most/up to/<=" maps to `lte`.
- **Why:** "At least a week" and "more than a week" mean different things to a recruiter (≥ 7 days vs > 7 days). Supporting both operators keeps each query faithful to what she typed, while "more than" stays strictly greater, per the original decision.
- **Evidence:** docs/SEARCH_SPEC.md §14 + ai-logs/antigravity/step-04-search-spec.md

## D-006 · Disagreement with AI · Ranking scores for non-name queries
- **Context:** Search results need a score (shown as a bar) even when the query has no name, e.g. "everyone except rejected".
- **AI suggestion:** Score by rank position, decreasing 0.1 per rank (1.0, 0.9, 0.8, …).
- **My decision:** Rejected it. Rank-normalized `score = 1 − i/n` instead.
- **Why:** The AI's formula goes negative after 10 results. "Everyone except rejected" returns 19 candidates, so the last ones would score −0.8 and break the score bar. `1 − i/n` always stays in (0, 1] for any result count.
- **Evidence:** The oracle proof on the 19-result query (min 0.05, max 1.0) in ai-logs/antigravity/step-05-seed-and-answer-key.md; docs/SEARCH_SPEC.md §10.


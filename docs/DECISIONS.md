# Decisions log

Every significant decision, and every place I disagreed with AI advice, is recorded here as it happens.
Entry format: **Context → AI suggestion → My decision → Why → Evidence** (commit, test or log link).
Type is either `Decision` or `Disagreement with AI`.

---

## D-001 · Decision · Frontend stack: server-rendered HTMX instead of React
- **Context:** The brief asks for a small single-recruiter web app. The role is Python-first, and the deadline is 3 days.
- **AI suggestion:** An earlier AI-generated design used React + Vite + TypeScript with a FastAPI backend.
- **My decision:** API-first FastAPI with a thin Jinja2 + HTMX + Alpine.js view layer. 100% Python, no Node toolchain.
- **Why:** <fill in, in my own words>
- **Evidence:** ai-logs/claude/00-system-design-and-steps.md (stack comparison section)

## D-002 · Decision · Database: hardened SQLite, portable to PostgreSQL
- **Context:** The audit trail must be immutable, and transitions must be reliable.
- **AI suggestion:** <fill in>
- **My decision:** SQLite (WAL, STRICT tables, CHECK constraints, triggers) via SQLAlchemy Core + Alembic.
- **Why:** <fill in>
- **Evidence:** ai-logs/claude/00-system-design-and-steps.md

## D-003 · Disagreement with AI · Planning docs are git-ignored
- **Context:** Where SYSTEM_DESIGN.md, IMPLEMENTATION_PLAN.md and instructions.md should live.
- **AI suggestion:** Commit them in the repo root (Claude's default for decision D1).
- **My decision:** Keep them in the root but git-ignored.
- **Why:** <fill in>
- **Evidence:** .gitignore; ai-logs/claude/00-system-design-and-steps.md

## D-004 · Decision · StatusIs model extended with at_stage for rejected-from stage tracking
- **Context:** Recruiter queries like "rejected at Interview" could not be captured by `StatusIs(status=rejected)` alone because the rejected-from stage was not tracked in the AST.
- **AI suggestion:** Add an optional `at_stage: Stage | None = None` field to `StatusIs` or create a `RejectedAtStage(stage: Stage)` clause.
- **My decision:** Accepted `StatusIs(status="rejected", at_stage=Stage)`. Valid only when `status = "rejected"` and `negate = False`. Rejection at Hired triggers `INVALID_REJECT_STAGE` error. SQL filters `candidate_state.status = 'rejected' AND candidate_state.stage = :at_stage`.
- **Why:** Enables precise candidate retrieval by the exact stage from which they were rejected, matching recruiter intent while enforcing that Hired candidates can never be rejected.
- **Evidence:** docs/SEARCH_SPEC.md §14 + ai-logs/antigravity/step-04-search-spec.md

## D-005 · Decision · TimeInStage op extended with gte and lte comparators
- **Context:** `TimeInStage.op` only supported strict `gt` and `lt`, which could not differentiate "more than a week" (> 7d) from "at least a week" (>= 7d).
- **AI suggestion:** Extend `TimeInStage.op` to `Literal["gt", "gte", "lt", "lte"]` or map "at least N days" to `gte`.
- **My decision:** Accepted `TimeInStage.op` as `Literal["gt", "gte", "lt", "lte"]`. "more than/over" maps to `gt`, "at least/no less than/>=" maps to `gte`, "less than/under" maps to `lt`, and "at most/up to/<=" maps to `lte`.
- **Why:** Distinguishes strict duration boundaries (> 7 days) from inclusive duration boundaries (>= 7 days) deterministically across both rules and power token syntax (`days>=7`, `days<=3`).
- **Evidence:** docs/SEARCH_SPEC.md §14 + ai-logs/antigravity/step-04-search-spec.md


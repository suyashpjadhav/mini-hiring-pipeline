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

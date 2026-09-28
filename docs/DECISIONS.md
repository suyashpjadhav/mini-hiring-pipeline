# Decisions log

Every place I rejected, changed, or overrode an AI suggestion, written when it happened.
Format: Context → AI suggestion → My decision → Why → Evidence.

## 1. Backend language: TypeScript → Python
- **Context:** Choosing the stack during system design (Claude chat, day 0).
- **AI suggestion:** A single Next.js + TypeScript app (API routes + SQLite via Drizzle).
- **My decision:** Python 3.12 + FastAPI for the backend, search, LLM layer and evals;
  React + TypeScript only for the UI.
- **Why:** The role is Python-first and the recruiter stressed Python in the screening call;
  the search engine, LLM fallback and evals are the core of the app and belong in Python.
  Cost: a separate frontend and ~1–2 extra hours of setup, accepted.
- **Evidence:** ai-logs/00-claude-system-design.md (stack discussion).

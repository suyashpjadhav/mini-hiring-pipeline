---
trigger: always_on
---

# Mini Hiring Pipeline — Agent Rules

## 1. Sources of truth
- `SYSTEM_DESIGN.md` (architecture, §-numbered), `IMPLEMENTATION_PLAN.md` (steps) and `instructions.md` (brief) are in the repo root. They are git-ignored on purpose: open them by explicit path and never guess their content.
- Before planning, read every § section the prompt references. If a prompt conflicts with SYSTEM_DESIGN.md, stop and ask.
- Generated docs go in `docs/`. Decisions are logged in `docs/DECISIONS.md`.

## 2. Pre-flight (every task)
1. Run `git status`. The tree must be clean except for files this step will touch; otherwise stop and report.
2. If `scripts/check.py` exists, run `uv run python -m scripts.check`. It must be green before you change anything.
3. State the step number, goal, the files you will create or modify, and your assumptions. In Planning mode, wait for approval.

## 3. Locked stack and architecture (SYSTEM_DESIGN §3, §4, §15)
- Python 3.12 + uv only: FastAPI, Jinja2, HTMX, Alpine.js (CSP build), SQLite via SQLAlchemy 2.0 Core, Alembic, Pydantic v2. No Node, npm, React, ORM models or runtime CDNs.
- API-first: business logic lives only in `service.py` files. `app/api` and `app/web` are thin adapters and never import each other.
- Pure core: `pipeline/domain`, `search/parser` and `search/engine` do no I/O, import no frameworks, and never call `datetime.now()`. Use the injected Clock.
- Only `repo.py` files touch the DB. Only `service.py` calls repos. Only `search/llm/gemini.py` touches the network.
- Never add a dependency that isn't in SYSTEM_DESIGN §3. If you think one is needed, raise a DISAGREE (§7 below) and ask.

## 4. Code quality
- Full type hints; `mypy --strict` clean; ruff lint and format clean.
- No placeholders, TODOs, stub `pass` bodies or fake implementations, unless the plan explicitly says an empty module is fine.
- Small, single-purpose functions; docstrings on public functions; raise domain errors from `domain/errors.py`, never bare exceptions.
- Every behaviour change ships with tests in the same step. Tests are deterministic: FixedClock, no network, no real time.

## 5. Security (SYSTEM_DESIGN §16)
- Bound parameters only. Never build SQL from strings or user text.
- Jinja autoescape stays on. Never use `|safe` on user data. No inline `<script>` and no `style=""` attributes (strict CSP).
- Every state-changing HTML route is CSRF-protected.
- Never open, create, edit, print or commit `.env` or any secret. Use `.env.example` only.
- Never log candidate names, emails or raw search queries.

## 6. Windows / PowerShell terminal
- Never chain commands with `&&`. Run them separately.
- Run all Python tooling via `uv run ...`. Add dependencies only with `uv add` / `uv add --dev`; never `pip install`.
- No interactive commands (use non-interactive flags). Start servers as background processes and stop them when done.
- Quote paths: the workspace path contains a space.
- Never run destructive commands (`git reset --hard`, `git push --force`, recursive deletes, deleting the database) without asking first.

## 7. Tests and disagreements
- Never delete, skip or weaken a test, or change its expected values, to make it pass.
- If the design, the prompt or a test seems wrong, stop and write:
  `DISAGREE: <what the design/prompt says> → <what you propose> → <why> → <evidence>`
  then wait for my decision.
- Never modify files the prompt marks as human-authored, beyond what the prompt explicitly allows.

## 8. Post-flight (end of every task)
1. Run `uv run python -m scripts.check` (once it exists) and show the final output.
2. Tick every "Done when" item of the step in IMPLEMENTATION_PLAN.md, with evidence (command output, test names, file paths).
3. Write `ai-logs/antigravity/step-NN-<slug>.md` using the template in `ai-logs/README.md`. Fill every section except `## Raw transcript`, which the human fills.
4. Propose a conventional commit message. Do NOT commit or push unless the prompt says so.

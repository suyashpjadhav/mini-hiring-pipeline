# PROJECT RULES — Mini Hiring Pipeline

## File locations
- Planning docs in the repo ROOT are git-ignored and must never be committed:
  SYSTEM_DESIGN.md (the design — source of truth), IMPLEMENTATION_PLAN.md (the steps),
  instructions.md (the original assignment brief). private/ is also git-ignored.
- Generated docs are committed under docs/.
- If code, docs and a prompt disagree, stop and ask me. Never guess.

## Pre-flight (start of EVERY task, before planning)
1. Run git status; the tree must be clean (otherwise tell me what is uncommitted).
2. If code exists, confirm the previous step's checks still pass.
3. Read the SYSTEM_DESIGN.md sections and IMPLEMENTATION_PLAN.md step this task depends on,
   and inspect every existing file you will touch.
4. List your assumptions and anything ambiguous before writing code.

## Process
- Do only the step I give you. Show a short plan first (in Planning mode), wait for approval.
- Tests first for domain and search code.
- If you want to deviate from SYSTEM_DESIGN.md, write "DEVIATION:" + reason and wait.
- If you think the design is wrong, write "DISAGREE:" + reason + alternative and wait.
- No dependencies beyond SYSTEM_DESIGN.md §3 without asking.
- Never delete, skip, or weaken a test to make it pass. If a test looks wrong, explain and ask.
- Never read, print, or commit backend/.env or anything in private/.

## Windows / PowerShell
- Terminal is PowerShell: no "&&"; use ";" or separate commands.
- If PowerShell blocks npm/npx ("running scripts is disabled"), use npm.cmd / npx.cmd.
- Never leave a command waiting on interactive input: use non-interactive flags
  (npx -y, shadcn init --defaults). If a prompt is unavoidable, stop and tell me its text.
- Run dev servers (uvicorn, npm run dev) as background processes and stop them when done.

## Backend (Python 3.12, uv, FastAPI, Pydantic v2, SQLAlchemy Core, SQLite, rapidfuzz)
- Run everything through uv (uv run ..., uv add ...). Never use pip directly.
- Type hints everywhere; mypy --strict and ruff must be clean.
- Follow the folder tree in SYSTEM_DESIGN.md §13 exactly.
- features/pipeline/domain, features/search/parser, features/search/engine are PURE:
  no fastapi, sqlalchemy, network, or datetime.now().
- Only repo.py touches the DB. Only service.py calls repos. Routers only call services.
- Never UPDATE or DELETE stage_events. Every state change = one transaction in the service.
- Time comes from the Clock protocol (app/shared/clock.py). Store UTC only.
- Domain errors come from domain/errors.py and are mapped to {code,message,hint} in api/errors.py.
- LLM code lives only in features/search/llm/, never sees candidate data, and its output
  is validated by QueryAST and the same validator as the rule parser.

## Frontend (React + Vite + TypeScript strict, Tailwind v4, shadcn/ui, TanStack Query)
- No "any". Components hold no business logic; data goes through each feature's hooks.ts.
- Features import each other only via index.ts. API types come from src/shared/api/schema.d.ts.
- Theme per SYSTEM_DESIGN.md §11: earth-neutral tokens, Cormorant Garamond only for the page
  title and drawer name, Poppins elsewhere, 24px radius cards, pill buttons, dark round
  primary button, glass only on drawer and search overlay, no photos, WCAG AA contrast,
  6 board columns fit at 1440px.

## Security (applies to every step)
- Secrets: never hardcode keys or tokens. Config only via pydantic-settings from backend/.env.
  backend/.env.example contains empty placeholders only. Never log or print the API key.
- SQL: parameterized queries only (SQLAlchemy text() with bound parameters). Never build SQL
  with f-strings, % formatting or concatenation from any input, including search terms.
- Input validation: every request body and query param is a Pydantic model with limits:
  full_name 1-120 chars, email max 254 chars with a simple format check, note max 1000 chars,
  search q 1-200 chars, tz must be a valid IANA zone (reject otherwise with a clear message).
- Errors: never return stack traces or raw exception text to clients. Unexpected errors ->
  500 {code:"INTERNAL", message:"Something went wrong"}; log details server-side only.
- CORS: not needed (Vite proxy in dev, same origin in review mode). Never allow "*".
- Frontend: never use dangerouslySetInnerHTML or eval; render all user and LLM text as plain text.
- LLM / prompt injection: treat the search query as untrusted. The model receives only the query,
  stage list, date and timezone - no candidate data, no tools, no system secrets. Its output must
  parse as QueryAST and pass the validator, otherwise it is discarded. The model never produces
  SQL or code that gets executed.
- Dependencies: only packages from SYSTEM_DESIGN.md §3; commit lockfiles (uv.lock,
  package-lock.json).
- Static analysis: ruff must include the "S" (flake8-bandit security) rule set; tests may
  ignore S101 (assert) only.

## End of every step
1. From backend/: uv run ruff check . ; uv run mypy app ; uv run lint-imports ; uv run pytest -q
   (skip any that don't apply yet). If frontend changed, from frontend/: npm run lint ; npm run build
2. Security review of the step's changes: list any new inputs, queries, secrets, or LLM
   calls, and confirm each follows the Security rules above.
3. Show all output. Fix failures before finishing.
4. Post-flight: re-read the step's "Done when" list in IMPLEMENTATION_PLAN.md and tick each
   item with evidence (test name, command output, or screenshot). Say plainly if anything
   is not done.
5. Stage changes (git add - never private/, root planning docs, or .env), then run the secret
   scan on staged changes; it must print nothing:
   git diff --cached | Select-String -Pattern 'AIza[0-9A-Za-z_-]{20,}|sk-[A-Za-z0-9]{20,}|(api[_-]?key|secret|token|password)\s*[:=]\s*[^\s"'']{8,}'
   If it matches, unstage, remove the secret, and tell me. Then commit with the step's commit
   message and push.

## Dependency audit (only at Steps 6, 15 and 20)
- Backend (from backend/):
  uv export --no-hashes --no-emit-project --format requirements-txt -o audit-req.txt ;
  uvx pip-audit -r audit-req.txt --no-deps --disable-pip ; Remove-Item audit-req.txt
- Frontend (from frontend/): npm audit --omit=dev
- Report findings; upgrade anything high or critical, then re-run the checks.

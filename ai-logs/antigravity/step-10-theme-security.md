# Step 10 — Design system, base layout, security middleware
- Date: 2026-09-30
- Tool / model / mode: Antigravity · Gemini 3.6 Flash · Fast
- Prompt: Deliver the themed page shell and the security plumbing that every later screen relies on.

## Summary
Delivered themed base shell (`base.html`, `_header.html`, `pages/index.html`), §13 design tokens (`tokens.css`), application styles (`app.css`), plain ES2020 frontend script (`app.js` with Alpine CSP toasts & timer, HTMX CSRF/Timezone header setup, client timezone cookie init), security middleware stack (`security.py` with CSP headers, double-submit CSRF, API guard), web template render helper (`render.py`), and web test suite (`test_web_security.py`, `test_web_base.py`, `test_render.py`).

## Files changed
- `app/web/static/vendor/VERSIONS.md`
- `app/web/static/css/tokens.css`
- `app/web/static/css/app.css`
- `app/web/static/js/app.js`
- `app/web/templates/base.html`
- `app/web/templates/shared/_header.html`
- `app/web/templates/pages/index.html`
- `app/core/security.py`
- `app/web/deps.py`
- `app/web/render.py`
- `app/web/routes/pages.py`
- `app/main.py`
- `tests/api/test_health.py`
- `tests/web/conftest.py`
- `tests/web/test_web_security.py`
- `tests/web/test_web_base.py`
- `tests/web/test_render.py`
- `ai-logs/antigravity/step-10-theme-security.md`
- `ai-logs/README.md`

## Decisions and disagreements
- Relaxed CSP only for `/docs` and `/openapi.json` to allow FastAPI Swagger UI scripts/styles from `https://cdn.jsdelivr.net` and `'unsafe-inline'` bootstrap initializer scripts.
- Implemented Alpine CSP components using name-based property and method references without inline JavaScript expressions.
- Used Starlette `Request.headers.get("cookie")` parsing for double-submit CSRF and client timezone cookie initialization.

## Issues hit and fixes
- Starlette `Jinja2Templates` autoescape parameter: removed explicit `autoescape=True` kwarg as Starlette handles Jinja autoescaping defaults natively.
- Ruff `S105` hardcoded password rule on `csrf_token` test assignment: resolved with `# noqa: S105`.
- Starlette middleware `__init__` parameter typing: simplified `CSRFMiddleware` constructor by reading settings dynamically from `request.app.state`.
- TestClient lifespan database initialization: added `tests/web/conftest.py` with `client` fixture running lifespan migrations on temporary SQLite test DBs.

## Verification evidence
- `uv run python -m scripts.check`: 100% PASS on all quality gates (ruff check, ruff format, mypy, lint-imports, 62 pytest tests, secret scan).
- Headers verified via uvicorn background process:
  - `/` returned `Content-Security-Policy: default-src 'self'; script-src 'self'; ...` and `set-cookie: csrftoken=...; HttpOnly; Path=/; SameSite=strict`.
  - `/docs` returned relaxed CSP `script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; ...`.
- SHA-256 hashes recorded in `app/web/static/vendor/VERSIONS.md`.

## Raw transcript
<!-- pasted by the human, unedited apart from removed secrets or personal data -->

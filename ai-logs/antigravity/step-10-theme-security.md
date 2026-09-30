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
<!-- # ROLE
You are a Senior Frontend-Security Engineer for server-rendered Python apps (FastAPI + Jinja2 + HTMX + Alpine.js CSP build).
You ship strict Content-Security-Policy pages with zero inline script or style, double-submit CSRF, and a clean design-token system.

# CONTEXT (read by explicit path)
@SYSTEM_DESIGN.md: §10.2 (view routes, HTML error policy, timezone plumbing), §13 (UI spec: tokens, screens, CSP-compatible front-end rules), §16 (security table: CSRF, CSP, headers, API guard)
@docs/TEST_PLAN.md: every Step 10 row (use those names)
The human has ALREADY downloaded these files (do not download or modify them):
app/web/static/vendor/htmx.min.js (2.0.4), app/web/static/vendor/alpine-csp.min.js (@alpinejs/csp 3.14.8),
app/web/static/fonts/{cormorant-garamond-500,cormorant-garamond-600,poppins-400,poppins-500}.woff2

# OBJECTIVE
Deliver the themed page shell and the security plumbing that every later screen relies on.
No board, drawer or search yet (Steps 11–14).

# FILES
## app/web/static/vendor/VERSIONS.md
For each vendored file: the package, version, source URL (jsDelivr), license (htmx 0BSD, Alpine MIT, fonts SIL OFL 1.1) and SHA-256, computed with `Get-FileHash -Algorithm SHA256`.

## app/web/static/css/tokens.css
- The EXACT §13.1 tokens as CSS custom properties on `:root`.
- `@font-face` rules for the 4 self-hosted fonts (`font-display: swap`).
- A spacing scale, radii and a shadow.

## app/web/static/css/app.css
- A reset.
- Body: `--bg` background, Poppins, `--ink` text.
- Header layout (§13.2):
  - the serif wordmark "Pipeline." plus the job title in small caps;
  - a centred underline-style search input (disabled placeholder "Search candidates… (coming soon)");
  - a dark round "+" button (disabled until Step 11).
- Button styles: `.btn-round` (dark), `.btn-pill` (outline).
- Card base `.card` (radius 24px, surface, shadow).
- Toast stack (top-right).
- `.htmx-indicator` styles (because htmx-config disables its injected styles).
- Visible `:focus-visible` rings. WCAG AA contrast. Responsive down to 1024px.

## app/web/templates/base.html
- `<!doctype html>`, `lang="en"`, charset, viewport.
- `<meta name="htmx-config" content='{"includeIndicatorStyles":false,"allowEval":false,"allowScriptTags":false,"selfRequestsOnly":true}'>`
- `<meta name="csrf-token" content="{{ csrf_token }}">`
- CSS links.
- Scripts, all external with `defer`, in this ORDER: `htmx.min.js`, `js/app.js`, then `alpine-csp.min.js`. Alpine must load last, after `app.js` has registered its components on `alpine:init`.
- Blocks `title` and `content`.
- The header partial.
- A toast region: `<div x-data="toasts" aria-live="polite">` rendered with Alpine CSP-safe directives only.
- NO inline `<script>`, NO `style=""` attributes, NO event-handler attributes (`onclick` etc.), NO `hx-on`.

## app/web/templates/shared/_header.html and pages/index.html
- `index.html` extends base.
- It shows the header plus a calm hero line: "{{ job_title }} · {{ total }} candidates" (the total from `PipelineService.board()`).
- The board comes in Step 11.

## app/web/static/js/app.js (plain ES2020, no build step)
- On `alpine:init`:
  - register `Alpine.data("toasts", …)` (add/dismiss, auto-dismiss after 4 s);
  - register `Alpine.data("timer", …)` (reads `data-since` epoch ms from `$el`, updates a "3d 4h 12m" text every second, cleans up its interval on destroy).
  - Alpine CSP build rules: directives may only reference properties and methods by name. No inline expressions like `count + 1`.
- On `htmx:configRequest`: add the `X-CSRF-Token` header (from the meta tag) and the `X-Timezone` header (`Intl.DateTimeFormat().resolvedOptions().timeZone`).
- On `DOMContentLoaded`: set a cookie `tz=<zone>; path=/; SameSite=Strict`.
- Listen for the `toast` event (dispatched by HTMX from `HX-Trigger`) and push `{kind, message}` into the toasts component.

## app/core/security.py
- `SecurityHeadersMiddleware`:
  - **Default CSP, EXACTLY** as in §16: `default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'`.
  - Plus `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`, and a `Permissions-Policy` with everything off.
  - For `/docs` and `/openapi.json` ONLY, a relaxed CSP that allows what FastAPI's Swagger UI needs: `https://cdn.jsdelivr.net` for scripts and styles, `'unsafe-inline'` for its bootstrap script and styles, and `https://fastapi.tiangolo.com` for images. Document why in a comment.
- `CSRFMiddleware` (double-submit):
  - If the `csrftoken` cookie is missing, generate `secrets.token_urlsafe(32)` and set it as HttpOnly, SameSite=Strict, Path=/, Secure only when `app_env == "prod"`.
  - Expose it as `request.state.csrf_token`.
  - For POST, PUT, PATCH and DELETE on `/ui/*`, require an `X-CSRF-Token` header equal to the cookie (`hmac.compare_digest`). Otherwise respond 403 with a plain message.
- `ApiGuardMiddleware`: unsafe methods on `/api/*` require `Content-Type: application/json` (otherwise 415 with the JSON error shape), and a present `Origin` must match the request host (otherwise 403 with the JSON error shape).
- `add_security_middleware(app, settings)` registers all three in the correct order.

## app/web/render.py and app/web/deps.py
- A shared `Jinja2Templates` (autoescape on) and `render(request, template, context, *, toast: tuple[str, str] | None = None, status_code=200)`.
- It injects `csrf_token`, `job_title` and `tz` into every template.
- When `toast` is given, it sets the `HX-Trigger` header to `{"toast": {"kind", "message"}}`.
- `resolve_request_tz(request, default)`: the `X-Timezone` header, then the `tz` cookie, then the default, validated via `app.core.timeutil.resolve_tz`.

## app/web/routes/pages.py (edit) and app/main.py (edit)
- `/` renders `pages/index.html` through `render()`.
- Mount `/static` (StaticFiles) and call `add_security_middleware`.

## Tests (tests/web/, names from docs/TEST_PLAN.md Step 10 rows)
- `test_web_security.py`:
  - `test_csp_headers_present`: the exact CSP on `/`; the relaxed CSP only on `/docs`.
  - `test_csrf_token_required_on_posts`: using a minimal test-only FastAPI app with the middleware and a dummy `POST /ui/ping`: no header → 403; a wrong token → 403; a matching token → 200.
  - The cookie flags (HttpOnly, SameSite=Strict).
  - The API guard: a form-encoded POST to `/api/v1/candidates` → 415; `Origin: https://evil.example` → 403.
- `test_web_base.py`:
  - `/` returns 200 with the csrf meta, the htmx-config meta, and the scripts in the right order;
  - BeautifulSoup finds NO `<script>` without `src`, NO element with a `style` attribute, and NO `on*` attributes;
  - `/static/vendor/htmx.min.js` and one font return 200.
- `test_render.py`: tz resolution priority (header > cookie > default; an invalid value → default); the `HX-Trigger` toast header shape.

# CONSTRAINTS
- mypy `--strict` and ruff clean. No new dependencies. `app.web` must not import `app.api`, and vice versa.
- All existing tests must still pass. The API tests must send JSON; if the new guard breaks any, fix the TEST, not the guard.

# DO NOT
- Do not modify vendored files, the domain, repo, migrations, docs/ or the planning docs. No board, drawer or search. Do not commit.

# SELF-VERIFICATION (mandatory; report)
1. The full `uv run python -m scripts.check` output.
2. With uvicorn running in the background:
   - `Invoke-WebRequest http://127.0.0.1:8000/ | Select-Object -ExpandProperty Headers`: show the CSP and Set-Cookie;
   - the same request for `/docs` (the relaxed CSP).

   Stop the server afterwards.
3. The contents of VERSIONS.md.
4. `git status --short`.
5. Write `ai-logs/antigravity/step-10-theme-security.md` and append its index row. Propose the commit message.
10:24 AM
Pre-flight & Task Execution Summary
Step: 10 — Design system, base layout, security middleware
Goal: Deliver the themed page shell and security plumbing (strict CSP, double-submit CSRF, API guard, design tokens, Alpine CSP directives, Jinja rendering, and test suite).
Files Created / Modified:


app/web/static/vendor/VERSIONS.md


app/web/static/css/tokens.css


app/web/static/css/app.css


app/web/static/js/app.js


app/web/templates/base.html


app/web/templates/shared/_header.html


app/web/templates/pages/index.html


app/core/security.py


app/web/deps.py


app/web/render.py


app/web/routes/pages.py


app/main.py


tests/api/test_health.py


tests/web/conftest.py


tests/web/test_web_security.py


tests/web/test_web_base.py


tests/web/test_render.py


ai-logs/antigravity/step-10-theme-security.md


ai-logs/README.md
Mandatory Self-Verification Evidence
1. Full Quality Gate Check (uv run python -m scripts.check)
text
=== Running ruff check ===
All checks passed!
=== Running ruff format --check ===
78 files already formatted
=== Running mypy ===
Success: no issues found in 76 source files
=== Running lint-imports ===
=============
Import Linter
=============
---------
Contracts
---------
Analyzed 65 files, 136 dependencies.
------------------------------------
Core logic is pure KEPT
Layering KEPT
Pipeline does not depend on search KEPT
Contracts: 3 kept, 0 broken.
=== Running pytest ===
..............................................................           [100%]
============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\BIT\Desktop\Hiring Pipeline\mini-hiring-pipeline\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
62 passed, 1 warning in 11.92s
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
2. Live HTTP Headers (Uvicorn background process verification)
Root Route (GET http://127.0.0.1:8000/) Headers:

text
STATUS: 200
HEADERS:
  date: Wed, 30 Sep 2026 05:37:48 GMT
  server: uvicorn
  content-length: 1679
  content-type: text/html; charset=utf-8
  set-cookie: csrftoken=GTmN1yECLL5yZMsmThNiKHDF96BpHsKp-WOB7Zu2zos; HttpOnly; Path=/; SameSite=strict
  content-security-policy: default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'
  x-content-type-options: nosniff
  referrer-policy: same-origin
  permissions-policy: accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()
  connection: close
Docs Route (GET http://127.0.0.1:8000/docs) Relaxed CSP Headers:

text
STATUS: 200
HEADERS:
  date: Wed, 30 Sep 2026 05:39:22 GMT
  server: uvicorn
  content-length: 1019
  content-type: text/html; charset=utf-8
  set-cookie: csrftoken=oEl7kZ9_8IA-B3SrHWy7lOj6td7P-7dAXM4ks1E_AsA; HttpOnly; Path=/; SameSite=strict
  content-security-policy: default-src 'self'; script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; font-src 'self'; img-src 'self' data: https://fastapi.tiangolo.com; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'
  x-content-type-options: nosniff
  referrer-policy: same-origin
  permissions-policy: accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()
  connection: close
(The uvicorn background process was stopped cleanly afterwards.)

3. Contents of 

app/web/static/vendor/VERSIONS.md
markdown
# Vendored Dependencies & Assets
This file documents third-party JavaScript dependencies and font assets vendored directly in `app/web/static/`.
| File | Package | Version | Source URL | License | SHA-256 Hash |
| --- | --- | --- | --- | --- | --- |
| `app/web/static/vendor/htmx.min.js` | `htmx.org` | 2.0.4 | `https://cdn.jsdelivr.net/npm/htmx.org@2.0.4/dist/htmx.min.js` | 0BSD | `E209DDA5C8235479F3166DEFC7750E1DBCD5A5C1808B7792FC2E6733768FB447` |
| `app/web/static/vendor/alpine-csp.min.js` | `@alpinejs/csp` | 3.14.8 | `https://cdn.jsdelivr.net/npm/@alpinejs/csp@3.14.8/dist/cdn.min.js` | MIT | `C98F46291087F0F93C9CDEFB682D120FE1D2B3DCB649DE83CFC1AD5B1FAC58E4` |
| `app/web/static/fonts/cormorant-garamond-500.woff2` | `@fontsource/cormorant-garamond` | 5.x | `https://cdn.jsdelivr.net/npm/@fontsource/cormorant-garamond@5/files/cormorant-garamond-latin-500-normal.woff2` | SIL OFL 1.1 | `8197BF53615DDC8C423F444C7F0EEC63B7FA0BA093FCFBEC60DFDD28429B0FC8` |
| `app/web/static/fonts/cormorant-garamond-600.woff2` | `@fontsource/cormorant-garamond` | 5.x | `https://cdn.jsdelivr.net/npm/@fontsource/cormorant-garamond@5/files/cormorant-garamond-latin-600-normal.woff2` | SIL OFL 1.1 | `AE062B6D5AE308E7EDF61B28B07B9984BBB6E961B1F34D9B2C2F4389C33F21EA` |
| `app/web/static/fonts/poppins-400.woff2` | `@fontsource/poppins` | 5.x | `https://cdn.jsdelivr.net/npm/@fontsource/poppins@5/files/poppins-latin-400-normal.woff2` | SIL OFL 1.1 | `7D93459D86585BFCDBB7E0376056226ADB25821EE54B96236FE2123E9560929F` |
| `app/web/static/fonts/poppins-500.woff2` | `@fontsource/poppins` | 5.x | `https://cdn.jsdelivr.net/npm/@fontsource/poppins@5/files/poppins-latin-500-normal.woff2` | SIL OFL 1.1 | `CD36DE204ACA2D5FA263A731F7C20009B5E3D754BA1F1E03C33E93A48F3E7446` |
4. git status --short Output
text
 M app/main.py
 M app/web/routes/pages.py
 M tests/api/test_health.py
?? ai-logs/antigravity/step-10-theme-security.md
?? app/core/security.py
?? app/web/deps.py
?? app/web/render.py
?? app/web/static/
?? app/web/templates/
?? tests/web/conftest.py
?? tests/web/test_render.py
?? tests/web/test_web_base.py
?? tests/web/test_web_security.py
Step Log & Proposed Commit Message
Created AI step log artifact: 

ai-logs/antigravity/step-10-theme-security.md
Updated index in 

ai-logs/README.md
Proposed Commit Message:

text
feat(web): design tokens, base layout, CSRF and CSP
 -->

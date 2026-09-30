# Step 11 — Board, card actions, add candidate
- Date: 2026-09-30
- Tool / model / mode: Antigravity · Gemini 3.6 Flash · Fast
- Prompt: Build FR-1 to FR-4 in the UI: the board grouped by stage, add candidate, advance and reject.

## Summary
Delivered FR-1 to FR-4 in the UI:
- Grouped Kanban board partial (`_board.html`) with 6 columns (Applied, Screening, Interview, Offer, Hired, Rejected), serif headers, candidate counts, total/active summary, and horizontal scrolling under 1280px.
- Candidate card template (`_card.html`) with duration-based status badges (`badge-sage` < 3d, `badge-ochre` 3-7d, `badge-terracotta` > 7d, `badge-rejected`), round Advance button (`→`), and pill Reject button with inline Alpine `confirmReject` panel. Final outcome cards (Hired / Rejected) render zero `<form>` and zero `<button>` elements.
- Add candidate modal template (`_add_dialog.html`) using native `<dialog>` and Alpine `modal` component, handling inline validation errors with `HX-Retarget: #dialog` and `HX-Reswap: innerHTML`.
- Pure display formatting helper (`formatting.py`) for duration strings and duration/status CSS classes with unit tests.
- Web route handlers (`app/web/routes/candidates.py`) for `/ui/board`, `/ui/candidates/new`, `/ui/candidates` (POST), `/ui/candidates/{id}/advance` (POST), and `/ui/candidates/{id}/reject` (POST) following domain error and validation toast policy.
- Updated `index.html` and `_header.html` to integrate board partial and header "+" button `hx-get`.
- Registered `confirmReject` and `modal` components in `app.js`.
- Added CSS styles in `app.css` for board grid, columns, cards, badges, confirm panel, and modal dialog.
- Comprehensive web test suite in `tests/web/` covering column counts, badge styling, final card invariants, add candidate form validation, advance/reject flow, stale version error toast, 404 error toast, CSRF protection, and CSP cleanliness.

## Files changed
- `app/web/formatting.py`
- `app/web/render.py`
- `app/web/routes/candidates.py`
- `app/web/routes/pages.py`
- `app/web/static/js/app.js`
- `app/web/static/css/app.css`
- `app/web/templates/board/_board.html`
- `app/web/templates/board/_card.html`
- `app/web/templates/candidates/_add_dialog.html`
- `app/web/templates/pages/index.html`
- `app/web/templates/shared/_header.html`
- `app/main.py`
- `tests/unit/test_web_formatting.py`
- `tests/web/test_web_board.py`
- `tests/web/test_web_cards.py`
- `tests/web/test_web_candidates.py`
- `ai-logs/antigravity/step-11-board.md`
- `ai-logs/README.md`

## Decisions and disagreements
- Domain errors (such as stale version, final outcome, candidate not found) on HTML form POSTs return HTTP 200 with current board partial and error toast via `HX-Trigger`, preserving HTMX DOM swap behavior and consistency.
- Form validation errors on `POST /ui/candidates` return HTTP 200 with `HX-Retarget: #dialog` and `HX-Reswap: innerHTML` to re-render inline field errors inside the modal without closing it.
- Card badge text and status class resolution logic was isolated into pure formatting helpers (`formatting.py`) and registered into Jinja filters/globals in `render.py`.
- Final outcome cards (Hired / Rejected) omit all form and button tags completely as specified.

## Issues hit and fixes
- FastApi `Form` parameter default in `Annotated`: changed `Annotated[str | None, Form(None)]` to `Annotated[str | None, Form()] = None` to satisfy FastAPI dependency parser rules.
- BeautifulSoup tag text matching in `test_web_board.py`: normalized whitespace using `" ".join(h2.text.split())` for exact column title matching.
- Ruff lint errors: removed unused imports/variables, converted `datetime.timezone.utc` to `datetime.UTC`, resolved docstring hyphen characters, and ran `ruff format`.

## Verification evidence
- `uv run python -m scripts.check`: 100% PASS on all quality gates (ruff check, ruff format, mypy, lint-imports, 72 pytest tests, secret scan).
- `uv run pytest tests/web -vv`: 17 passed in 3.68s.
- Clean git status except touched step 11 files.

## Raw transcript
<!-- # ROLE
You are a Senior Full-Stack Python Engineer specializing in HTMX + Jinja2 hypermedia UIs and Alpine.js (CSP build).
You build accessible, server-rendered interfaces where the server is the single source of truth.

# CONTEXT (read by explicit path)
@SYSTEM_DESIGN.md: §2.1, §10.2 (view routes + HTML error policy: domain errors → 200 + error toast), §13.2 (board, card, states), §13.3 (CSP rules)
@docs/TEST_PLAN.md: the Step 11 rows (use those names)
Existing (read, reuse, don't break): app/web/{render,deps}.py, app/web/templates/base.html, app/web/static/{css,js}/*, app/core/security.py, app/features/pipeline/service.py

# OBJECTIVE
Build FR-1 to FR-4 in the UI: the board grouped by stage, add candidate, advance and reject.

# ROUTES (app/web/routes/candidates.py; thin: parse → service → render)
| Method | Path | Behaviour |
|---|---|---|
| GET | `/ui/board` | `board/_board.html` |
| GET | `/ui/candidates/new` | `candidates/_add_dialog.html` |
| POST | `/ui/candidates` | Form fields `full_name`, `email` (optional; validate with Pydantic `EmailStr` via TypeAdapter). **Success:** board partial + toast `Added {name}` + `HX-Trigger` event `close-dialog`. **Validation or domain error:** re-render the dialog with inline field errors, status 200, with `HX-Retarget: #dialog` and `HX-Reswap: innerHTML` |
| POST | `/ui/candidates/{id}/advance` | Form field `expected_version`. Success: board partial + toast `{name} moved to {stage}` (or `{name} was hired 🎉`) |
| POST | `/ui/candidates/{id}/reject` | Form field `expected_version`. Success: board partial + toast `{name} rejected at {stage}` |

- **Any DomainError** (stale version, final outcome, not found): status 200, the CURRENT board partial, and an error toast carrying `err.message`.
- **Invalid ids** → a NOT_FOUND toast.

# TEMPLATES
- `board/_board.html`:
  - root `<div id="board">`, containing a summary row `{{ total }} candidates · {{ active }} active`;
  - a 6-column grid (Applied, Screening, Interview, Offer, Hired, Rejected), each a `<section aria-labelledby>` with a serif title and count;
  - the empty state "No one here yet";
  - horizontal scroll below 1280px; all 6 columns fit at 1440px.
- `board/_card.html`:
  - the name (a plain `<span class="card-name" data-id>`; it becomes the drawer link in Step 12), a muted email and a time badge;
  - **active cards:** the badge reads "In stage 3d 4h", with a class by duration: `badge-sage` < 3d, `badge-ochre` 3–7d, `badge-terracotta` > 7d;
  - **Advance:** `.btn-round` "→", with `aria-label="Advance {name} to {next}"`, a form with `hx-post`, `hx-target="#board"`, `hx-swap="outerHTML"`, and a hidden `expected_version`;
  - **Reject:** a `.btn-pill` opening an inline confirm panel (Alpine component `confirmReject`, CSP-safe: `open`/`toggle`/`close` methods). The panel holds the real `hx-post` "Yes, reject" button and "Cancel";
  - **final cards:** the badge reads "Hired 3d ago" or "Rejected at Interview · 2d ago". NO action buttons or forms at all.
- `candidates/_add_dialog.html`:
  - a native `<dialog>` with Alpine component `modal`, whose `init()` calls `showModal()` and which listens for the `close-dialog` event to `close()`;
  - a form with `hx-post="/ui/candidates"`, `hx-target="#board"`, `hx-swap="outerHTML"`;
  - labelled inputs, inline error text with `aria-describedby`, Cancel and Add buttons.
- `pages/index.html`: the header, then `{% include "board/_board.html" %}`, plus `<div id="dialog"></div>`.
  - Enable the header "+" button: `hx-get="/ui/candidates/new"`, `hx-target="#dialog"`.
  - Move the hero count into the board summary, so it refreshes after every action.

# SUPPORTING CODE
- `app/web/formatting.py` (pure): `format_duration(seconds) -> str` ("3d 4h", "5h 12m", "just now") and `duration_class(seconds) -> str`. Add unit tests.
- `app.js`: register `confirmReject` and `modal` with Alpine.data (CSP build: directives reference properties and methods by name only).
- CSS for the board, columns, cards, badges, the confirm panel and the dialog, using the `tokens.css` variables only.

# TESTS (tests/web/; get the CSRF cookie and token from `GET /` first, then send `X-CSRF-Token`)
- `test_board_render_columns_and_counts`: seed a few candidates via the service → 6 columns, correct counts, the correct badge classes (FixedClock).
- `test_final_outcome_cards_no_buttons`: Hired and Rejected cards contain no `<form>` and no `button`, and show outcome labels.
- Add success (the board contains the name; the `HX-Trigger` has a toast and `close-dialog`); add with an invalid email or empty name → the dialog with an error and `HX-Retarget: #dialog`.
- Advance moves the card; reject moves it to Rejected; a stale `expected_version` → 200, the board unchanged, and an error toast with STALE text.
- A POST without the CSRF header → 403.
- The rendered HTML has no inline script, no `style` attributes and no `on*` attributes.

# CONSTRAINTS / DO NOT
- Strict CSP stays as is: no inline script or style, no `hx-on`, and CSP-safe Alpine only.
- mypy `--strict` and ruff clean. No new dependencies. No business logic in routes or templates beyond display formatting.
- Don't touch the domain, repo, migrations, API, docs/ or the planning docs. No drawer or search yet. Do not commit.

# SELF-VERIFICATION (report)
1. The full `uv run python -m scripts.check` output.
2. `uv run pytest tests/web -vv` (the list of tests).
3. `git status --short`.
4. Write `ai-logs/antigravity/step-11-board.md` and append its index row. Propose the commit message.
11:31 AM
Step 11 Self-Verification Report: Board, Card Actions & Add Candidate
1. Full uv run python -m scripts.check Output
text
=== Running ruff check ===
All checks passed!
=== Running ruff format --check ===
84 files already formatted
=== Running mypy ===
Success: no issues found in 82 source files
=== Running lint-imports ===
=============
Import Linter
=============
---------
Contracts
---------
Analyzed 67 files, 149 dependencies.
------------------------------------
Core logic is pure KEPT
Layering KEPT
Pipeline does not depend on search KEPT
Contracts: 3 kept, 0 broken.
=== Running pytest ===
........................................................................ [100%]
============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
72 passed, 1 warning in 9.35s
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
2. uv run pytest tests/web -vv Output
text
tests/web/test_render.py::test_timezone_resolution_priority PASSED       [  5%]
tests/web/test_render.py::test_render_hx_trigger_toast PASSED            [ 11%]
tests/web/test_web_base.py::test_base_layout_structure PASSED            [ 17%]
tests/web/test_web_base.py::test_no_inline_scripts_styles_or_handlers PASSED [ 23%]
tests/web/test_web_base.py::test_static_files_served PASSED              [ 29%]
tests/web/test_web_board.py::test_board_render_columns_and_counts PASSED [ 35%]
tests/web/test_web_candidates.py::test_add_candidate_success_and_validation_errors PASSED [ 41%]
tests/web/test_web_candidates.py::test_advance_and_reject_actions PASSED [ 47%]
tests/web/test_web_candidates.py::test_stale_expected_version_error_toast PASSED [ 52%]
tests/web/test_web_candidates.py::test_invalid_candidate_id_not_found_toast PASSED [ 58%]
tests/web/test_web_candidates.py::test_post_without_csrf_forbidden PASSED [ 64%]
tests/web/test_web_candidates.py::test_rendered_html_csp_cleanliness PASSED [ 70%]
tests/web/test_web_cards.py::test_final_outcome_cards_no_buttons PASSED  [ 76%]
tests/web/test_web_security.py::test_csp_headers_present PASSED          [ 82%]
tests/web/test_web_security.py::test_csrf_token_required_on_posts PASSED [ 88%]
tests/web/test_web_security.py::test_csrf_cookie_flags PASSED            [ 94%]
tests/web/test_web_security.py::test_api_guard PASSED                    [100%]
======================== 17 passed, 1 warning in 3.68s ========================
3. git status --short
text
 M ai-logs/README.md
 M app/main.py
 M app/web/render.py
 M app/web/routes/pages.py
 M app/web/static/css/app.css
 M app/web/static/js/app.js
 M app/web/templates/pages/index.html
 M app/web/templates/shared/_header.html
?? ai-logs/antigravity/step-11-board.md
?? app/web/formatting.py
?? app/web/routes/candidates.py
?? app/web/templates/board/
?? app/web/templates/candidates/
?? tests/unit/test_web_formatting.py
?? tests/web/test_web_board.py
?? tests/web/test_web_candidates.py
?? tests/web/test_web_cards.py
4. Documentation & Commit Proposal
Log file created: 

ai-logs/antigravity/step-11-board.md
Index updated: 

ai-logs/README.md
Proposed Commit Message: feat(web): board UI, add candidate modal, advance and reject actions

11:31 AM
1:13 PM
Change Request Verification Report: Top Stage Bar Navigation & View Routing
1. Full uv run python -m scripts.check Output
text
=== Running ruff check ===
All checks passed!
=== Running ruff format --check ===
84 files already formatted
=== Running mypy ===
Success: no issues found in 82 source files
=== Running lint-imports ===
=============
Import Linter
=============
---------
Contracts
---------
Analyzed 67 files, 150 dependencies.
------------------------------------
Core logic is pure KEPT
Layering KEPT
Pipeline does not depend on search KEPT
Contracts: 3 kept, 0 broken.
=== Running pytest ===
........................................................................ [ 97%]
..                                                                       [100%]
============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
74 passed, 1 warning in 9.79s
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
2. uv run pytest tests/web -vv Output
text
tests/web/test_render.py::test_timezone_resolution_priority PASSED       [  5%]
tests/web/test_render.py::test_render_hx_trigger_toast PASSED            [ 10%]
tests/web/test_web_base.py::test_base_layout_structure PASSED            [ 15%]
tests/web/test_web_base.py::test_no_inline_scripts_styles_or_handlers PASSED [ 21%]
tests/web/test_web_base.py::test_static_files_served PASSED              [ 26%]
tests/web/test_web_board.py::test_board_stage_bar_and_view_routing PASSED [ 31%]
tests/web/test_web_board.py::test_full_page_view_routing PASSED          [ 36%]
tests/web/test_web_candidates.py::test_add_candidate_success_and_validation_errors PASSED [ 42%]
tests/web/test_web_candidates.py::test_advance_and_reject_actions PASSED [ 47%]
tests/web/test_web_candidates.py::test_action_with_view_parameter_rerenders_same_view PASSED [ 52%]
tests/web/test_web_candidates.py::test_stale_expected_version_error_toast PASSED [ 57%]
tests/web/test_web_candidates.py::test_invalid_candidate_id_not_found_toast PASSED [ 63%]
tests/web/test_web_candidates.py::test_post_without_csrf_forbidden PASSED [ 68%]
tests/web/test_web_candidates.py::test_rendered_html_csp_cleanliness PASSED [ 73%]
tests/web/test_web_cards.py::test_final_outcome_cards_no_buttons PASSED  [ 78%]
tests/web/test_web_security.py::test_csp_headers_present PASSED          [ 84%]
tests/web/test_web_security.py::test_csrf_token_required_on_posts PASSED [ 89%]
tests/web/test_web_security.py::test_csrf_cookie_flags PASSED            [ 94%]
tests/web/test_web_security.py::test_api_guard PASSED                    [100%]
======================== 19 passed, 1 warning in 2.92s ========================
3. git status --short
text
 M ai-logs/antigravity/step-11-board.md
 M app/web/routes/candidates.py
 M app/web/routes/pages.py
 M app/web/static/css/app.css
 M app/web/templates/board/_board.html
 M app/web/templates/board/_card.html
 M docs/DECISIONS.md
 M tests/web/test_web_board.py
 M tests/web/test_web_candidates.py
4. Documentation Log
Added ## Change request: top stage bar section to 

ai-logs/antigravity/step-11-board.md
.
Appended D-007 entry to 

docs/DECISIONS.md
.
Updated SYSTEM_DESIGN.md §13.2 Board spec to match top stage bar and stacked/single section views. -->

## Change request: top stage bar
- **Summary:** Replaced 6-column grid layout with top stage bar navigation + default `view=all` stacked sections or single stage grid `view=<Stage>`.
- **Files changed:**
  - `SYSTEM_DESIGN.md`
  - `docs/DECISIONS.md`
  - `app/web/routes/candidates.py`
  - `app/web/routes/pages.py`
  - `app/web/templates/board/_board.html`
  - `app/web/templates/board/_card.html`
  - `app/web/static/css/app.css`
  - `tests/web/test_web_board.py`
  - `tests/web/test_web_candidates.py`
- **Decisions:**
  - Standardized canonical view names (`all`, `Applied`, `Screening`, `Interview`, `Offer`, `Hired`, `Rejected`) with case-insensitive input normalization and fallback to `all`.
  - Added hidden `view` input to card Advance and Reject forms so actions preserve current active view.
  - Candidate creation (`POST /ui/candidates`) always re-renders `view=all` with `HX-Push-Url: /?view=all`.
- **Issues hit and fixes:** None. All web and core quality gates passed cleanly.


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
<!-- pasted by the human -->

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


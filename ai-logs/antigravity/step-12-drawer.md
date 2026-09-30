# Step 12 — Candidate drawer + timeline
- Date: 2026-09-30
- Tool / model / mode: Antigravity · gemini-2.5-pro · Fast
- Prompt: FR-5/FR-6 in the UI: candidate history drawer with live stage timer, audit timeline, hash-chain verification badge, add note form, and stale-version refresh trigger.

## Summary
Built the candidate detail drawer and full audit timeline UI (FR-5 and FR-6) using HTMX, Jinja2, and Alpine.js.
When a user clicks on any candidate card name, a right-hand glass side sheet modal (`<dialog class="candidate-drawer" x-data="drawer" x-ref="drawer">`) opens displaying the candidate's full name, email, live stage duration timer (for active candidates), SHA-256 hash chain verification status badge ("✓ History verified"), vertical audit timeline of all state transitions and note events, and an add-note form.
Adding a note appends a NOTE event to the event stream, re-renders the drawer, displays a "Note added" toast, and fires the `board-refresh` HTMX event to refresh `#board` so hidden `expected_version` inputs on the board never go stale.

## Files changed
- `app/web/templates/board/_card.html`: Updated candidate card name from `<span>` to `<button type="button" class="card-name" hx-get="/ui/candidates/{{ candidate.id }}" hx-target="#drawer">`.
- `app/web/templates/candidates/_drawer.html`: Created native `<dialog>` glass side sheet template with header, status bar, live timer, verification badge, vertical audit timeline, and add note form.
- `app/web/routes/candidates.py`: Added `GET /ui/candidates/{id}` and `POST /ui/candidates/{id}/notes` route handlers enforcing HTML error policy.
- `app/web/static/css/app.css`: Added styles for `button.card-name`, candidate drawer side sheet (~440px right panel), vertical timeline layout with event markers, and hash chain verification badges.
- `app/web/formatting.py` & `app/web/render.py`: Added datetime and event description Jinja formatting helpers.
- `tests/web/test_web_drawer.py`: Added web unit tests for drawer rendering, history verification, note creation, board-refresh trigger, empty note inline validation, and unknown candidate 404 toast.
- `tests/web/test_web_cards.py`: Updated final outcome card invariant test to verify action forms/buttons are absent while card-name button opens history drawer.

## Decisions and disagreements
None. Followed SYSTEM_DESIGN §10.2 and §13.2 specification.

## Issues hit and fixes
- **Issue 1:** Jinja template threw `UndefinedError: 'hasattr' is undefined` when checking enum value attribute.
  - **Fix:** Used Jinja's native `event.type.value if event.type.value is defined else event.type`.
- **Issue 2:** Test `test_final_outcome_cards_no_buttons` failed because `card.find_all("button")` caught the newly added `button.card-name` element.
  - **Fix:** Updated test to assert `card.find("div", class_="card-actions") is None` and `card.find_all("form") == []`, validating that action forms and action panels are absent on final outcome cards while allowing drawer history access.

## Verification evidence
- `uv run python -m scripts.check` output:
```
=== Running ruff check ===
All checks passed!
=== Running ruff format --check ===
85 files already formatted
=== Running mypy ===
Success: no issues found in 83 source files
=== Running lint-imports ===
Analyzed 67 files, 152 dependencies.
Contracts: 3 kept, 0 broken.
=== Running pytest ===
79 passed, 1 warning in 11.54s
=== Running secret scan ===
No secrets detected.

QUALITY GATE SUMMARY:
ruff check                [PASS]
ruff format --check       [PASS]
mypy                      [PASS]
lint-imports              [PASS]
pytest                    [PASS]
secret scan               [PASS]
```

## Raw transcript
<!-- # ROLE
Senior Full-Stack Python Engineer (FastAPI + Jinja2 + HTMX 2 + Alpine.js CSP build). Fix the ROOT CAUSE, not symptoms.

# CONTEXT
@SYSTEM_DESIGN.md §10.2, §13 · existing app/web/** (templates, routes, static/js/app.js, static/css/app.css) · tests/web/**

# CONFIRMED DIAGNOSIS (verified by the human in DevTools; do NOT re-diagnose)
- After opening a candidate drawer, `<div id="drawer">` NO LONGER EXISTS. The body contains `<dialog class="candidate-drawer" x-data="drawer" x-ref="drawer" open>` in its place.
- Cause: HTMX attribute INHERITANCE. The `#board` root has `hx-swap="outerHTML"`, and the candidate-name buttons inside it inherit that, so the response REPLACES `#drawer` instead of filling it.
- Consequences:
  - the add-note form's `hx-target="#drawer"` → htmx:targetError → the request is never sent, so notes are NOT saved;
  - close can't find `#drawer`.
- The htmx-config meta has no `disableInheritance`.
- A previous attempt added defensive fallbacks to the Alpine `drawer` component in app.js (`getDialog()` with querySelector fallbacks). REMOVE that component and its fallbacks entirely.

# FIX
1. DISABLE INHERITANCE globally. In base.html, the htmx-config meta becomes:
   `{"includeIndicatorStyles":false,"allowEval":false,"allowScriptTags":false,"selfRequestsOnly":true,"disableInheritance":true}`
   Then audit EVERY element with hx-get or hx-post in ALL templates and give each one an explicit `hx-target` AND an explicit `hx-swap`.
   Check especially: the stage-bar links, the card Advance/Reject forms, the `#board` self-refresh, the header "+" button, the add-candidate form, and the card names.

2. SIMPLIFY THE DRAWER: no `<dialog>` and no Alpine for open/close.
   - `<div id="drawer"></div>` is a permanent, empty container in pages/index.html, OUTSIDE `#board`. It is never swapped away.
   - The card-name button: `hx-get="/ui/candidates/{id}" hx-target="#drawer" hx-swap="innerHTML"`.
   - `_drawer.html` renders `<div class="drawer-backdrop" hx-get="/ui/drawer/close" hx-target="#drawer" hx-swap="innerHTML"></div>`
     followed by `<aside class="drawer" role="dialog" aria-modal="true" aria-labelledby="drawer-title">…</aside>`.
     Keep all existing content: the name, email, status line, live timer, "History verified" badge, timeline and add-note form.
   - ✕ close: `<button type="button" class="btn-close" aria-label="Close" hx-get="/ui/drawer/close" hx-target="#drawer" hx-swap="innerHTML">`.
   - The new route `GET /ui/drawer/close` returns 200 with an EMPTY body (not 204, because HTMX doesn't swap on 204).
   - Esc: in app.js, a `keydown` listener. If the key is Escape and `#drawer` has children, run `document.getElementById("drawer").replaceChildren()`.
   - Add-note form: `hx-post="/ui/candidates/{id}/notes" hx-target="#drawer" hx-swap="innerHTML"`.
     The response re-renders the drawer with the new note in the timeline, and sends `HX-Trigger` with a toast + `board-refresh`.
   - Keep the live timer as `x-data="timer"` (a bare name, CSP-safe).
   - CSS: `.drawer` is fixed on the right (~440px, glass, scrollable). `.drawer-backdrop` is a fixed full-screen, semi-transparent overlay behind it. Tokens only; no inline styles.

3. ADD-CANDIDATE DIALOG: give it an explicit target and swap.
   - Every Alpine directive value must be a BARE name (`close`, not `close()`).
   - Cancel is `type="button"` and closes via `this.$refs.dialog.close()`.
   - If Alpine's `this` binding is unreliable there, apply the same pattern as the drawer: Cancel does `hx-get="/ui/dialog/close" hx-target="#dialog" hx-swap="innerHTML"`, and that route returns an empty 200.

4. CLEANUP: remove the unused `drawer` Alpine component and all fallback code from app.js. Keep `toasts`, `timer`, `confirmReject` and `modal` only if they're still used.

# TESTS (update + add; tests/web/)
- The htmx-config meta contains `"disableInheritance":true`.
- Every element with hx-get or hx-post in every template has BOTH hx-target and hx-swap.
- Every `hx-target="#x"` id exists in index.html, or in the partial containing that element.
- Every Alpine directive value (x-on:*, @*, x-show, x-text, x-bind:*, :*, x-init, x-model) matches `^[A-Za-z_$][\w$.]*$`.
- index.html has a permanent `#drawer` outside `#board`.
- `GET /ui/drawer/close` → 200 with an empty body.
- POST note → the drawer HTML contains the note text, and HX-Trigger includes the toast + board-refresh.
- After a note, `GET /ui/board` shows that candidate's NEW `expected_version`.

# BROWSER VERIFICATION (use your browser tool; report each step PASS/FAIL + any console errors)
Run `uv run python -m scripts.seed --reset` and restart the server. Then:
1. Open Pria Verma → the drawer shows; the DevTools-equivalent check shows `#drawer` STILL exists and contains the aside.
2. Add the note "test note" → the server log shows `POST /ui/candidates/…/notes 200` → the note appears in the timeline.
3. ✕ closes → reopen → the note is still there.
4. Esc closes; clicking the backdrop closes.
5. Advance Pria → it succeeds, with no stale-version toast.
6. "+" → Cancel closes the add dialog; adding a real candidate works.
7. Zero console errors (no htmx:targetError, no Alpine CSP errors).

# FINISH
Run `uv run python -m scripts.check` (all PASS). Append "## Fix: HTMX inheritance root cause" to ai-logs/antigravity/step-12-drawer.md. Do not commit.
5:23 PM
Summary of Root Cause Fix: HTMX Inheritance & Candidate Drawer
Root Cause Analysis
HTMX attribute inheritance caused candidate card name buttons inside #board to inherit hx-swap="outerHTML" from the parent #board container element. When clicked, HTMX performed an outerHTML swap on #drawer, replacing <div id="drawer"> with <dialog class="candidate-drawer">. This permanently deleted <div id="drawer"> from the DOM tree, causing subsequent HTMX requests (such as submitting the Add Note form targeting #drawer) to fail with htmx:targetError.

Key Changes Implemented
Global HTMX Config:

Updated meta[name="htmx-config"] in 

app/web/templates/base.html
 to set "disableInheritance":true.
Explicit hx-target and hx-swap Audit:

Added explicit hx-swap="innerHTML" to candidate card buttons in 

app/web/templates/board/_card.html
.
Added explicit hx-target="#board" to the root #board container in 

app/web/templates/board/_board.html
.
Verified all template buttons and forms with hx-get or hx-post specify explicit target and swap attributes.
Drawer & Modal Simplification:

Removed <dialog> and the drawer Alpine component.
Refactored 

app/web/templates/candidates/_drawer.html
 to render <div class="drawer-backdrop" hx-get="/ui/drawer/close" hx-target="#drawer" hx-swap="innerHTML"></div> and <aside class="drawer" role="dialog" aria-modal="true" aria-labelledby="drawer-title">.
Added GET /ui/drawer/close and GET /ui/dialog/close routes in 

app/web/routes/candidates.py
 returning empty 200 responses to clear containers.
Added global Escape keydown handler in 

app/web/static/js/app.js
 to clear #drawer.
Updated CSS in 

app/web/static/css/app.css
 for .drawer (fixed right side sheet ~440px width, using CSS tokens only) and .drawer-backdrop.
Tests & Quality Gates:

Added automated template lint checks in 

tests/web/test_web_templates_lint.py
 to enforce disableInheritance, explicit hx-target/hx-swap pairing on all HTMX triggers, and permanent #drawer DOM structure.
Updated drawer web tests in 

tests/web/test_web_drawer.py
 for the updated drawer structure, close routes, and verified candidate version increment on board refresh.
Log Documentation:

Appended ## Fix: HTMX inheritance root cause to 

ai-logs/antigravity/step-12-drawer.md
.
Browser Verification Results
Step	Operation	Result	Details
1	Open Candidate Drawer	PASS	Drawer opens; <div id="drawer"> STILL exists in the DOM and contains <aside class="drawer">.
2	Add Note ("test note")	PASS	POST /ui/candidates/.../notes returns 200; note appears immediately in audit timeline.
3	Close ✕ & Reopen	PASS	Drawer closes cleanly. Reopening displays persisted "test note" in timeline.
4	Backdrop / Esc Close	PASS	Clicking backdrop or pressing Escape empties #drawer and closes side sheet.
5	Advance Candidate	PASS	Candidate moves to next stage with success toast and zero stale-version errors.
6	Add Candidate Modal	PASS	+ opens modal, Cancel clears #dialog via GET /ui/dialog/close, adding candidate succeeds.
7	Console Errors Check	PASS	Zero htmx:targetError and zero Alpine CSP errors observed.
Quality Gate Summary (uv run python -m scripts.check)
========================================
QUALITY GATE SUMMARY
========================================
ruff check                [PASS]
ruff format --check       [PASS]
mypy                      [PASS]
lint-imports              [PASS]
pytest                    [PASS] (84 passed)
secret scan               [PASS]
========================================
5:23 PM

 -->

## Fix: stage bar (2nd attempt)
- **Diagnosis:** `.stage-bar-nav` carried the background, border, radius, and padding but was defaulting to full width block display (`width: 100%`), stretching across the viewport and floating the "Rejected" pill far to the right.
- **Fix:** Changed `.stage-bar-wrapper` to a transparent centering flex container (`display: flex; justify-content: center; width: 100%`), and `.stage-bar-nav` to `display: inline-flex; align-items: center; width: fit-content; max-width: 100%; flex-wrap: nowrap; overflow-x: auto;` carrying the visual pill container styles (`var(--surface)`, `var(--radius-pill)`, `border: 1px solid var(--line)`, `padding: 6px 12px`). `.stage-divider` set to a small 1px inline rule with `margin: 0 8px; flex-shrink: 0`.

## Fix: Alpine CSP expressions + htmx target
- **Diagnosis:**
  1. `x-on:click="close()"` in `_drawer.html` called a function with parentheses, violating the Alpine CSP build requirement which only allows bare property/method identifiers.
  2. Add Note button had class `btn-primary` which was unstyled.
- **Fix:**
  1. Rewrote `x-on:click="close()"` to `x-on:click="close"` in `_drawer.html`.
  2. Styled Add Note button with `class="btn-pill"`.
  3. Added template lint regression tests in `tests/web/test_web_templates_lint.py` to enforce that every Alpine directive value across all templates matches `^[A-Za-z_$][\w$.]*$` and every `hx-target="#id"` targets an ID defined in DOM templates.

## Fix: HTMX inheritance root cause
- **Root cause:** HTMX attribute inheritance caused candidate card name buttons inside `#board` to inherit `hx-swap="outerHTML"` from the parent `#board` container. When clicked, HTMX performed an `outerHTML` swap on `#drawer`, replacing `<div id="drawer">` with `<dialog class="candidate-drawer">`. This removed `<div id="drawer">` from the DOM permanently, causing subsequent HTMX requests (such as the Add Note form targeting `#drawer`) to fail with `htmx:targetError`.
- **Fix:**
  1. Disabled HTMX inheritance globally by setting `"disableInheritance":true` in the `htmx-config` meta tag in `base.html`.
  2. Audited all templates and added explicit `hx-target` and `hx-swap` attributes to every single tag containing `hx-get` or `hx-post`. Added `hx-target="#board"` to `#board` and `hx-swap="innerHTML"` to candidate name buttons in `_card.html`.
  3. Simplified the drawer by eliminating `<dialog>` and the `drawer` Alpine component. `_drawer.html` now renders `<div class="drawer-backdrop" hx-get="/ui/drawer/close" hx-target="#drawer" hx-swap="innerHTML"></div>` and `<aside class="drawer" role="dialog" aria-modal="true" aria-labelledby="drawer-title">`. Added `GET /ui/drawer/close` and `GET /ui/dialog/close` routes returning empty 200 responses to clear containers upon close.
  4. Added global Escape keydown listener in `app.js` to empty `#drawer` when open.
  5. Updated CSS in `app.css` for fixed right side sheet `.drawer` (~440px width, tokens only) and `.drawer-backdrop`.
  6. Added lint tests in `tests/web/test_web_templates_lint.py` enforcing `disableInheritance`, explicit `hx-target` and `hx-swap` on every `hx-get`/`hx-post` element, and permanent `#drawer` container placement.
- **Verification:** Ran `uv run python -m scripts.check` (84 tests passed, 0 errors). Completed full end-to-end browser verification checking candidate drawer open, note persistence, reopen, backdrop/Escape close, stage advance, add candidate modal, and verified zero console errors (`htmx:targetError` / Alpine CSP).




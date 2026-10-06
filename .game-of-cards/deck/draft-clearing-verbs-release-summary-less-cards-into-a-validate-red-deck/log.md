## 2026-07-23T13:24:57Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

Which contract should hold?

1. **Gate the draft-clear**: `publish` / `status active` / `done` refuse
   (or interactively prompt) when `summary` is empty, mirroring the
   placeholder-scaffold gate. Strictest; may annoy quick claim flows.
2. **Warn, don't block**: draft-clearing verbs print a warning and proceed;
   validate stays the enforcement point. Cheapest, but keeps the
   verb-then-red-deck window open.
3. **Auto-stub**: draft-clear copies the H1/first body line into `summary`
   when missing. No red state, but silently authors frontmatter the human
   never wrote.

Option 1 matches the existing placeholder-scaffold precedent in
`_cmd_publish`; option 3 contradicts the repo's aversion to silent
mutations. A human should pick.


## 2026-10-06T05:22:31Z: decision recorded

Option 1: publish, status active and done (incl. --bundle) refuse to release a draft whose summary fails the published-card rule; validate and the verbs share one summary_problem() rule — Rodja 2026-10-06 (zauberzeug Zoe workspace card goc-publish-laesst-eine-karte-ohne-summary-in-den-stapel); matches the placeholder-scaffold gate already in publish, and option 3 would silently author frontmatter nobody wrote. Gate decision → none.

## 2026-10-06T05:25:55Z — Losing options

- **Option 2 (warn, don't block)** rejected: the downstream repo that hit this showed the warning would not be read — the cards came from an autonomous agent's `new` → `status active` → `done` flow, and the red only surfaced in the next validate run, by then without an owner.
- **Option 3 (auto-stub)** rejected: it would silently author frontmatter nobody wrote, against the repo's no-silent-mutation stance; a summary copied from the H1 also defeats the triage purpose the field exists for.

## 2026-10-06T05:25:55Z — Closure

- **What changed**: `goc/engine.py` — `summary_problem()` is the single summary rule for `validate` (messages unchanged) and for `summary_release_error()`, consulted by `publish`, `status active`, `done` and `done --bundle` (planning loop, before any write); help text of `goc new --summary`; draft-contract docs in the card-schema and create-card skill templates (mirrors and OpenClaw port regenerated).
- **Verification**: `reproduce.py` exit 0 on this branch, exit 1 on main f510cbe1 (all three verbs released a summary-less draft); `goc validate` green; `sync_plugin_assets.py --check` OK.
- **Audit**: no rubric configured; mechanical fix
- **Tests**: new `tests/test_draft_clearing_verbs_require_summary.py` (5, red before the change in the four refusal cases); 13 fixtures in `test_draft_guard_and_lifecycle`, `test_draft_queue_visibility` and `test_install` now give their released drafts a summary — no assertion changed.
- **Scope**: only the draft → published transition is gated; hand-written cards that never were drafts keep `validate` as their net.

## Closure verification (2026-10-06T05:25:56Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-10-06 — Closure' present

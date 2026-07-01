# Log

## 2026-07-01 — Closure

Surfaced during a `pull-card` session whose ready queue was empty (all
`human_gate: none` open cards carried active `waiting_on` overlays), then
fixed through in the same session.

**Fix:** added `and not card_is_draft(t)` to the `open_gated` comprehension
in `render_leverage_line` (`goc/engine.py`), so the leverage line's gated
candidate set matches the sibling open-only predicate `card_is_ready`. Draft
scaffolds no longer leak into the "Highest gated card" comparison.

**Verification:**
- `reproduce.py` now exits 0 (was exit 1): with only a draft gated card, the
  leverage line is omitted entirely.
- Added two regression tests in `tests/test_draft_queue_visibility.py`
  (`test_leverage_line_excludes_draft_scaffold`,
  `test_leverage_line_names_authored_gated_card`); confirmed the first fails
  on the pre-fix engine and passes after.
- Full suite green (680 tests); `uv run goc validate` clean.
- Re-synced the three plugin `goc/engine.py` mirrors
  (`scripts/sync_plugin_assets.py`); `test_plugin_mirror_parity` green.

**Closure audit:** no project rubric configured (empty finish-card hook);
mechanical single-site fix. It aligns with the `card_is_draft` docstring
contract — the single "not yet real" predicate all queue/scheduler/board/json
surfaces consult so the rule cannot drift per call site. This was the one
open-only surface that had drifted from it.

**Relationship:** third live instance of the drift catalogued by
`waiting-impedes-callers-reimplement-the-terminal-status-liveness-gate-and-drift`;
this card advances that umbrella. The eventual centralized live/open-only
helper (the umbrella's decision) subsumes this point-fix.

## Closure verification (2026-07-01T02:35:14Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [ ] log-md-closure-entry FAIL — no '## 2026-07-01 — Closure' section

## Closure verification (2026-07-01T02:35:23Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-07-01 — Closure' present

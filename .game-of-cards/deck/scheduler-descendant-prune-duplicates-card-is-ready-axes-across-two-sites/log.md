## 2026-05-31T02:22:56Z — Closure

- **What changed**: `goc/engine.py:1936` — introduce
  `card_is_workable_for_scheduler(card)` next to `card_is_ready`; both
  `value_for` (in `compute_values`, `engine.py:2087`) and
  `sort_default.live_direct` (`engine.py:2318`) now call the helper
  instead of enumerating the three rejection axes inline.
- **Coupling guard**: `tests/test_scheduler_workable_predicate_coupling.py`
  cross-products `status × human_gate × waiting_on` and asserts the
  helper agrees with `card_is_ready` except at
  `status=active ∧ gate=none ∧ waiting=None` (the documented
  active-allowed clause). A future axis added to `card_is_ready` that
  is not mirrored into the helper fails this test loudly.
- **Latent reproduce.py defect fixed in passing**: sibling 1's
  `compute-values-inherits-value-through-done-and-superseded-descendants/reproduce.py`
  was already exiting 1 on `main` before this refactor — its `_card`
  factory did not set `human_gate`, so the sibling-3 gate prune
  rejected the `open->open` live descendant case as if it were parked.
  Added an explicit `human_gate: "none"` default to the factory so all
  three sibling reproduce scripts exit 0 as the DoD requires.
- **Audit**: PASS — no rubric configured; mechanical refactor that
  extracts a named predicate for the live-AND-workable scheduler rule
  with no behavior change on current inputs (verified by the three
  sibling reproduce scripts and the full test suite).
- **Tests**: 348 passed / 0 failed (full `unittest discover -s tests`,
  includes the new coupling test); `uv run goc validate` clean; plugin
  mirrors synced (`scripts/sync_plugin_assets.py`).

## Closure verification (2026-05-31T02:23:15Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-31 — Closure' present

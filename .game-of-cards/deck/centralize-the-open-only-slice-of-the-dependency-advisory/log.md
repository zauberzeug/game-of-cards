## 2026-06-23T00:00:00Z — Closure

- **What changed**: `goc/engine.py` `dependency_advisory` — added a
  `queue_only` parameter that returns `([], False)` for any non-open card
  (on top of the existing terminal gate). `render_table` and
  `render_board`'s `card_cell` now call the `queue_only=True` form,
  dropping their inlined `t.status == "open"` guards; `render_json` keeps
  the default (terminal-only) form so the machine surface is unchanged.
- **Verification**: full suite 544 passed / 0 failed; targeted set
  (helper + verbose-table + board + JSON liveness) 26 passed. New
  `DependencyAdvisoryQueueOnlySliceTest` pins the slice and asserts table
  and board agree end-to-end per status.
- **Audit**: PASS — invokes the api-contract / meta-fix principle
  (centralize a guard that has already drifted into a shipping bug per
  un-centralized dimension; AGENTS.md "each renderer re-applies the same
  guard" shape).
- **Project impact**: n/a
- **Tests**: 544 passed / 0 failed / 0 xfailed
- **Bundled with**: n/a

## Closure verification (2026-06-23T13:23:49Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-06-23 — Closure' present

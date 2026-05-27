## 2026-05-27T01:59:43Z — Closure

- **What changed**: `goc/engine.py:1885` — `sort_default`'s tiebreak now counts only *live* direct `advances` targets (`live_direct` helper), mirroring the value-walk prune at engine.py:1751: dangling, terminal, and `waiting_on`-impeded targets contribute 0. Docstring updated to describe the live-edge semantic.
- **Verification**: reproduce.py exits 0 before / 1 after; equal-value pair (card-x with two `done` downstream vs older card-y with none) now breaks on `created`, putting older card-y first.
- **Audit**: PASS — no principle touched, mechanical fix (derivation gap: tiebreak realigned to the existing scheduler-axis prune invariant).
- **Project impact**: n/a
- **Tests**: 159 passed / 0 failed / 0 xfailed (+ 4 subtests).
- **Bundled with**: none

## Closure verification (2026-05-27T01:59:54Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present

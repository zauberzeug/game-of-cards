## 2026-05-26T00:00:00Z — Closure

- **What changed**: goc/engine.py — added `DOD_ANY_BOX` + `_dod_box_indices(lines)` (case-insensitive); `_apply_dod_rewrite` now routes box enumeration through the helper so it agrees with the canonical `DOD_OPEN_BOX`/`DOD_DONE_BOX` counters on `[x]`/`[X]`.
- **Verification**: reproduce.py exits 0 — `box_indices` len == canonical count (2); `idx:1` rewrite lands on `beta`, `[X] alpha` untouched. Under the old `[ x]` regex, `box_indices` len was 1 and the `beta` edit was dropped.
- **Audit**: PASS — no principle touched, mechanical fix (regex reconciliation).
- **Project impact**: n/a
- **Tests**: no pytest suite; `goc validate` clean, plugin mirrors synced.
- **Bundled with**: none

## Closure verification (2026-05-26T23:03:39Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present

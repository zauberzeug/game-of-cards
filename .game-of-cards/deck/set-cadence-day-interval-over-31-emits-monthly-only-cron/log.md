## 2026-06-22T09:10:00Z — Closure

- **What changed**: `scripts/set_cadence.py:84-93` — added an upper-bound guard rejecting `Nd` with N > 31 (mirrors the hour path's reject-out-of-range pattern); docstring updated to document the 1 ≤ N ≤ 31 range.
- **Verification**: `reproduce.py` now exits 0 (`interval_to_cron("40d", 15)` raises ValueError); `31d` boundary still translates to `0 0 */31 * *`.
- **Audit**: PASS — no principle touched, mechanical fix (bounds check on a cron field range).
- **Project impact**: n/a
- **Tests**: 15 passed / 0 failed (tests.test_set_cadence); full suite green.
- **Bundled with**: n/a

## Closure verification (2026-06-22T09:03:40Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-06-22 — Closure' present

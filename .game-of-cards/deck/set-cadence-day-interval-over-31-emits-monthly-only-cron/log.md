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

## 2026-07-09 — Post-close amendment

The upper bound this card added (`n > 31`) was off by one relative to its own
rationale: `*/31` enumerates day-of-month candidates {1, 32}, so it matches
only day 1 — the same monthly-only collapse this card classified as a silent
misconfiguration. The DoD's "asserts the valid boundary \"31d\" still
translates" blessed that boundary without checking the arithmetic. Follow-up
card [set-cadence-accepts-31d-which-collapses-to-monthly-only-cron](../set-cadence-accepts-31d-which-collapses-to-monthly-only-cron/)
tightened the guard to reject N > 30 and moved the supported-boundary test to
`30d`.

## 2026-06-15T05:40:00Z — Closure

- **What changed**: `goc/engine.py:1420-1437` — `validate_card` now appends a `closed_at predates created` error when both stamps parse to instants and `closed_at` is strictly before `created` (reusing `_waiting_until_instant`). Mirrors re-synced to the three plugin payloads.
- **Verification**: reproduce.py exits 0; flags both the months-apart inversion and the same-day intra-day datetime inversion, leaves the valid-ordering control clean. 5 new regression cases in `tests/test_validate_closed_at_ordering.py`.
- **Audit**: PASS — no principle touched, mechanical fix (cross-field coherence check, matches the existing hard-error treatment of `closed_at`/status coherence).
- **Project impact**: n/a
- **Tests**: 446 passed / 0 failed / 0 xfailed (full `unittest discover`).
- **Surfaced via**: queue-empty audit-deck pass during a pull-card run; fixed through in the same session (gate-free, single-site).

## Closure verification (2026-06-15T05:30:50Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-06-15 — Closure' present

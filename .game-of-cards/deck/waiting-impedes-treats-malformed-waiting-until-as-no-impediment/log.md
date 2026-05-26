## 2026-05-26T00:00:00Z — Closure

- **What changed**: `goc/engine.py:1603` — `waiting_impedes` now sets `until_date = None` on an unparseable `waiting_until` and falls through to the reason check instead of early-returning `False`.
- **Verification**: reproduce.py exits 0; the reason-plus-garbage-date card flips from `impeded=False` (defect) to `impeded=True`; the five control paths (reason-no-date, no-overlay, bare-future, bare-elapsed, reason-plus-future) are unchanged.
- **Audit**: PASS — no principle touched, mechanical fix (aligns behavior with the existing docstring contract).
- **Project impact**: n/a
- **Tests**: no pytest suite; `goc validate` clean; reproduce.py exit 0.

## Closure verification (2026-05-26T21:13:54Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present

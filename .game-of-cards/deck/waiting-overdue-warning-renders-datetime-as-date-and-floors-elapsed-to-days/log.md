## 2026-05-30T12:33:47Z — Closure

- **What changed**: `goc/engine.py:1493-1498` — `validate_waiting_overlay` now renders `waiting_until` via `_format_waiting_until_for_message` (echoes the stored shape: bare date stays `YYYY-MM-DD`, datetime keeps `YYYY-MM-DDTHH:MM:SSZ`) and renders elapsed time via `_format_elapsed` (minutes under 1h, hours under 1d, otherwise days).
- **Verification**: reproducer now exits 0 with `waiting_until=2026-05-30T23:00:00Z elapsed 1h ago`; new unit test file `tests/test_validate_waiting_overlay_message.py` covers datetime-echo, sub-day elapse, sub-hour elapse, multi-day no-regression, bare-date no-regression (string + `date` instance).
- **Audit**: PASS — no rubric configured; mechanical fix (rendered-message precision parity with the read guard contract `validate_waiting_overlay` already documents).
- **Project impact**: n/a
- **Tests**: 282 passed / 0 failed / 0 xfailed

## Closure verification (2026-05-30T12:33:58Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-30 — Closure' present

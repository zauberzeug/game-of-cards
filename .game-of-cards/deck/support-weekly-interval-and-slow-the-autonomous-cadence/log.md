## 2026-06-26 — exact weekly support + daily/weekly cadence

- `set_cadence.py`: added the `1w` spec → `<off> 0 * * 1` (exact weekly via
  the day-of-week field, Monday); `_SPEC_RE` now accepts `w`; `Nw` (N≥2)
  rejected. Weekly deliberately does NOT use the `<N>d` day-of-month path,
  which only approximates and realigns monthly — the DOW field is drift-free.
- Docstring + `tune-cadence` SKILL.md document the distinction.
- `tests/test_set_cadence.py`: added `1w` mapping + `2w` rejection tests.
- Applied: pull `13 0 * * *` (daily), audit `15 0 * * 1`, refine `45 0 * * 1`
  (weekly, Mondays). Idempotent re-run is a no-op.
- Returns the loop to the daily/weekly shape of run-pull-card-daily-and-audit-deck-weekly
  (2026-05-31), now tooling-managed and including refine-deck.
- Noted in passing: over the prior 5 days the autonomous loop itself audited
  and fixed a real set_cadence bug (>31-day intervals), commit b297882.
- Verified: test_set_cadence (17), goc validate, sync --check green.

## 2026-06-26 — Closure

Closed: all 4 DoD items met. Exact weekly (`1w` → day-of-week Monday)
implemented and documented as drift-free vs `7d`; cadence applied (pull daily,
audit/refine weekly) and idempotent. test + validate + sync green (only the
sandbox-only interactive-rebase guard test fails, as before; passes in CI).
Pending: push to main for the new crons to take effect.

## Closure verification (2026-06-26T02:56:59Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-06-26 — Closure' present

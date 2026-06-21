## 2026-06-21 — multi-day support + slower cadence

- `set_cadence.py` `interval_to_cron` now accepts `<N>d`: `1d` → daily,
  `Nd` (N≥2) → day-of-month `*/N` step. `0d`/garbage still rejected.
  Docstring + `tune-cadence` SKILL.md document the month-boundary
  realignment caveat (no exact every-N-days cron exists).
- `tests/test_set_cadence.py`: replaced the old multiday-rejected test with
  multiday-supported assertions (3d/7d) + a `0d` rejection test.
- Applied via the script: pull `13 */6 * * *` (every 6h, exact),
  audit `15 0 */3 * *`, refine `45 0 */3 * *` (every ~3 days).
- Reverses the parent card's deliberate multi-day rejection (amended there
  with a forward pointer).
- Verified: test_set_cadence, goc validate, sync --check green.

## 2026-06-21 — Closure

Closed: all 4 DoD items met. Multi-day intervals supported (with the honest
`*/N` day-of-month realignment caveat documented in script + skill); cadence
applied (pull every 6h, audit/refine every ~3 days) and idempotent. test +
validate + sync green (only the sandbox-only interactive-rebase guard test
fails, as before; passes in CI). Pending: push to main for the new crons to
take effect.

## Closure verification (2026-06-21T14:19:44Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-06-21 — Closure' present

## 2026-06-21 — moved pull-card to :13

- `set_cadence.py` WORKFLOWS["pull"] offset 0 → 13; docstring + `tune-cadence`
  SKILL.md offset notes updated to :13.
- Re-ran the script: pull-card.yml cron `0 * * * *` → `13 * * * *`, comment
  offset :13; idempotent re-run is a no-op.
- Why: GitHub's schedule queue is most congested at :00 (this repo dispatches
  ~85–90 min late, worst at the top of the hour); :13 dodges it. audit/refine
  already sit at :15/:45.
- Verified: test_set_cadence, goc validate, sync --check green. Parent card
  add-set-cadence-tooling-to-retune-autonomous-workflows amended.

## 2026-06-21 — Closure

Closed: all 3 DoD items met. pull-card now runs at `13 * * * *` (still hourly,
off the congested top-of-hour slot); applied via set_cadence.py (offset
constant 0→13), docs synced, idempotent re-run is a no-op. test_set_cadence +
goc validate + sync --check green (only the sandbox-only interactive-rebase
guard test fails, as before; passes in CI). Pending: push to main for the new
minute to take effect.

## Closure verification (2026-06-21T07:18:35Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-06-21 — Closure' present

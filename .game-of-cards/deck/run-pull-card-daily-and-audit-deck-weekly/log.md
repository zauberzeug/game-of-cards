## 2026-06-21 — cadence reversed (forward pointer)

The daily-pull / weekly-audit cadence this card set was deliberately
reversed while spare-token headroom was high: pull-card → hourly,
audit-deck → every 3h, plus a new refine-deck workflow every 3h. The
schedules are now managed by `scripts/set_cadence.py`. See
`add-set-cadence-tooling-to-retune-autonomous-workflows`. This card's
record stays accurate for the 2026-05-31 slowdown it made — closure is
not frozenness.

# Log

## 2026-07-18 — filed, implemented, closed (same session)

Requested cadence: pull-card hourly, audit-deck every 3 h, refine-deck
every 3 h offset at least 1 h from audit. The last constraint was not
expressible: `set_cadence.py` only had fixed *minute* offsets, so two
workflows on the same `Nh` interval always shared the hour slot (`*/N`),
30 minutes apart.

Extended the interval-spec grammar with an optional `+P` hour-phase
suffix (`3h+1` → hour field `1-23/3`). Chose a caller-facing suffix over
baking a fixed hour phase into `WORKFLOWS` so the phase only applies
where requested, and the managed `# cadence:` comment records the spec
verbatim — `--show` output alone reproduces the retune. Validation:
phase < N for sub-daily `Nh` (rejects the slot-dropping `3h+3` shape),
0–23 as hour-of-day for `24h`/`Nd`/`1w`, rejected outright for `1h`.
Invalid phases trip the existing all-or-nothing dry-run.

Applied: pull `13 * * * *`, audit `15 */3 * * *`, refine
`45 1-23/3 * * *` (refine trails each audit slot by 1 h 30 min).

Verification: 32 tests in `tests/test_set_cadence.py` (9 new), full
regression suite 742 tests OK, `goc validate` green. Closed and pushed
to main the same day — schedules only take effect from the default
branch.

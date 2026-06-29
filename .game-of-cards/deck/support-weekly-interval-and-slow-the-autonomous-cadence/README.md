---
title: support-weekly-interval-and-slow-the-autonomous-cadence
summary: "Slowed the autonomous loop to daily-pull / weekly-audit-and-refine and taught `set_cadence.py` the exact weekly interval that cadence needs."
status: done
stage: null
contribution: low
created: "2026-06-26T02:55:41Z"
closed_at: "2026-06-26T02:56:59Z"
human_gate: none
advances: []
advanced_by: []
tags: [infra, story]
definition_of_done: |
  - [x] MECHANICAL: `set_cadence.py` accepts `1w` → `<off> 0 * * 1` (exact weekly via the day-of-week field, Monday); `_SPEC_RE` accepts the `w` unit; `Nw` (N≥2) is rejected. The docstring and the `tune-cadence` SKILL.md document that `1w` is drift-free (unlike `7d`).
  - [x] TDD: `tests/test_set_cadence.py` asserts the `1w` mapping (offset 15 and 45) and `2w` rejection; `uv run python -m unittest tests.test_set_cadence` is green.
  - [x] MECHANICAL: applied cadence is pull-card `13 0 * * *` (daily), audit-deck `15 0 * * 1`, refine-deck `45 0 * * 1` (weekly, Mondays); each `# cadence:` comment matches its cron and an idempotent re-run is a no-op.
  - [x] MECHANICAL: `goc validate` + `sync --check` are green (suite unchanged modulo the sandbox-only interactive-rebase test).
worker: {who: Rodja Trappe, where: main}
---

# support-weekly-interval-and-slow-the-autonomous-cadence

Slow the autonomous loop to daily-pull / weekly-audit-and-refine, and
teach `set_cadence.py` the **exact weekly** interval that needs.

## What changed

| Workflow | Before | After | Cron |
|---|---|---|---|
| `pull-card.yml` | every 6h `13 */6 * * *` | daily | `13 0 * * *` |
| `audit-deck.yml` | every 3d `15 0 */3 * *` | weekly (Mon) | `15 0 * * 1` |
| `refine-deck.yml` | every 3d `45 0 */3 * *` | weekly (Mon) | `45 0 * * 1` |

This returns the loop to the daily/weekly shape first set in
[run-pull-card-daily-and-audit-deck-weekly](../run-pull-card-daily-and-audit-deck-weekly/)
(2026-05-31), now driven by the `set_cadence.py` tooling and including
the refine-deck workflow that didn't exist back then.

## Tool change: exact weekly via day-of-week

"Every week" is the one multi-day cadence cron expresses **exactly** —
through the day-of-week field (`* * * * 1` = every Monday), with no
month-boundary drift. So weekly does NOT go through the `<N>d`
day-of-month `*/N` path (which only approximates and realigns monthly);
it gets its own `1w` spec mapping to `<offset> 0 * * 1`.

Monday matches this repo's historical weekly audit slot (`0 2 * * 1`).
`Nw` for N≥2 (every-other-week etc.) has no clean cron and is rejected,
same honesty as the multi-day path.

## Out of scope

- The minute offsets (`:13` / `:15` / `:45`) and `MAX_ITERATIONS` — unchanged.
- Which weekday weekly lands on — fixed at Monday; changing it would be a
  follow-up if ever wanted.

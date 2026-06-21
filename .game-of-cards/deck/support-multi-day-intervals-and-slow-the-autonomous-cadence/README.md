---
title: support-multi-day-intervals-and-slow-the-autonomous-cadence
status: done
stage: null
contribution: low
created: "2026-06-21T14:18:17Z"
closed_at: "2026-06-21T14:19:44Z"
human_gate: none
advances: []
advanced_by: []
tags: [infra, story]
definition_of_done: |
  - [x] MECHANICAL: `set_cadence.py` `interval_to_cron` accepts `<N>d`: `1d` → `<off> 0 * * *`, `Nd` (N≥2) → `<off> 0 */N * *`; `0d` is rejected. The script docstring and the `tune-cadence` SKILL.md document the month-boundary realignment caveat.
  - [x] TDD: `tests/test_set_cadence.py` asserts the multi-day mapping (`3d`, `7d`) and `0d` rejection; `uv run python -m unittest tests.test_set_cadence` is green.
  - [x] MECHANICAL: applied cadence is pull-card `13 */6 * * *`, audit-deck `15 0 */3 * *`, refine-deck `45 0 */3 * *`; each `# cadence:` comment matches its cron and an idempotent re-run is a no-op.
  - [x] MECHANICAL: `goc validate` + `sync --check` are green (suite unchanged modulo the sandbox-only interactive-rebase test); the parent card `add-set-cadence-tooling-to-retune-autonomous-workflows` is amended with a `log.md` forward pointer (it had recorded multi-day as rejected).
worker: {who: Rodja Trappe, where: main}
---

# support-multi-day-intervals-and-slow-the-autonomous-cadence

Dial the autonomous loop down to a low-churn cadence, and teach
`set_cadence.py` the multi-day intervals that requires.

## What changed

| Workflow | Before | After | Cron |
|---|---|---|---|
| `pull-card.yml` | hourly `13 * * * *` | every 6 hours | `13 */6 * * *` |
| `audit-deck.yml` | every 3h `15 */3 * * *` | every 3 days | `15 0 */3 * *` |
| `refine-deck.yml` | every 3h `45 */3 * * *` | every 3 days | `45 0 */3 * *` |

## Tool change: multi-day interval support

`set_cadence.py` previously **rejected** day intervals other than `1d`
(see the parent card
[add-set-cadence-tooling-to-retune-autonomous-workflows](../add-set-cadence-tooling-to-retune-autonomous-workflows/),
which deliberately refused them). This card reverses that: `interval_to_cron`
now maps `<N>d` (N≥2) to a day-of-month `*/N` cron step.

### The honest caveat

There is **no exact "every N days" cron.** `*/3` in the day-of-month
field fires on days 1, 4, 7, …, 28, 31, then realigns at the next month
start — so the gap across a month boundary is shorter than 3 days (e.g.
Jan 31 → Feb 1 is one day). This is the standard cron approximation and
is fine for low-frequency hygiene/audit passes; it is documented in the
script docstring and the `tune-cadence` skill. Anyone needing exact
72-hour spacing would need an external timer, not cron.

## Out of scope

- pull-card's `6h` is a clean divisor of 24, so it's exact (`*/6` hours);
  only the `3d` audit/refine intervals carry the realignment caveat.
- `MAX_ITERATIONS` and the minute offsets (`:13` / `:15` / `:45`) —
  unchanged.

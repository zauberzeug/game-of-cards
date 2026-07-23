---
title: retune-cadence-to-12h-pull-and-2d-audit-refine
summary: "Pure knob turn via scripts/set_cadence.py: dialed the autonomous cadence back from hourly pull / 3-hourly audit-refine to pull-card every 12 hours and audit-deck/refine-deck every two days. Refine keeps a +1 hour phase so it still launches at least an hour after audit's slot."
status: done
stage: null
contribution: low
created: "2026-07-19T03:29:08Z"
closed_at: "2026-07-19T03:29:46Z"
human_gate: none
advances: []
advanced_by: []
tags: [infra]
definition_of_done: |
  - [x] MECHANICAL: Cadence on disk: pull-card `12h` (`13 */12 * * *`), audit-deck `2d` (`15 0 */2 * *`), refine-deck `2d+1` (`45 1 */2 * *`)
  - [x] PROCESS: Committed and pushed to main so the schedule takes effect
worker: {who: Rodja Trappe, where: main}
---

# retune-cadence-to-12h-pull-and-2d-audit-refine

## Briefing

Dial the autonomous cadence back from the 2026-07-18 setting (hourly
pull, 3-hourly audit/refine): pull-card every 12 hours, audit-deck and
refine-deck every two days.

Pure knob turn via `scripts/set_cadence.py` — no engine or tool change
needed. Refine keeps a `+1` hour phase so it still launches ≥1 h after
audit's slot (the standing separation preference from the predecessor
card `set-cadence-hour-phase-for-same-interval-offset-and-hourly-retune`);
with the shared minute offsets alone they would fire 30 minutes apart.

`2d` is the documented cron approximation: day-of-month `*/2` fires on
odd days, so a 31-day month ends with consecutive-day runs (31st → 1st).

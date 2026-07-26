---
title: set-cadence-hour-phase-for-same-interval-offset-and-hourly-retune
summary: "Extended scripts/set_cadence.py's interval grammar with an optional +P hour-phase suffix (3h+1 → `45 1-23/3 * * *`) so two workflows sharing an interval can be offset by whole hours, validated all-or-nothing before any workflow file is touched. Applied the requested retune: pull-card hourly, audit-deck every 3 hours, refine-deck 3h+1 so it launches at least an hour after each audit slot."
status: done
stage: null
contribution: medium
created: "2026-07-18T13:15:17Z"
closed_at: "2026-07-18T13:19:10Z"
human_gate: none
advances: []
advanced_by: []
tags: [infra]
definition_of_done: |
  - [x] TDD: `interval_to_cron` accepts an optional `+P` hour-phase suffix (`3h+1` → `45 1-23/3 * * *` at offset 45) with validation: phase < N for `Nh`, phase ≤ 23 for `24h`/`Nd`/`1w`, rejected for `1h`
  - [x] TDD: Invalid phases (`1h+1`, `3h+3`, `1d+24`) are rejected by the all-or-nothing dry-run before any workflow file is touched
  - [x] TDD: Tests cover phase parsing, cron generation, rejection cases, and round-trip through `retune` (32 tests in tests/test_set_cadence.py)
  - [x] MECHANICAL: Cadence retuned on disk: pull-card `1h` (`13 * * * *`), audit-deck `3h` (`15 */3 * * *`), refine-deck `3h+1` (`45 1-23/3 * * *`) — refine launches ≥1 h after each audit slot
  - [x] MECHANICAL: Skill doc `.claude/skills/tune-cadence/SKILL.md` and the script docstring document the phase syntax
  - [x] EMPIRICAL: Regression suite green (742 tests OK); change committed and pushed to main so the schedule takes effect
worker: {who: Rodja Trappe, where: main}
---

# set-cadence-hour-phase-for-same-interval-offset-and-hourly-retune

## Briefing

The requested cadence is: pull-card hourly, audit-deck every 3 hours,
refine-deck every 3 hours **offset at least 1 hour from audit**.

`scripts/set_cadence.py` cannot express that last constraint. Its only
anti-collision mechanism is the fixed per-workflow *minute* offset
(pull `:13`, audit `:15`, refine `:45`). Two workflows on the same
`Nh` interval both get an hour field of `*/N`, so audit and refine
would fire in the same hour slot 30 minutes apart — audit files a new
card and refine mutates the deck board while the audit agent may still
be running (both are ~30-min agent runs; pull-card already hit its
30-minute timeout on 2026-07-18).

## Design

Extend the interval spec grammar with an optional hour-phase suffix
`+P` (caller-facing, recorded verbatim in the managed `# cadence:`
comment so `--show` self-documents):

- `Nh+P` (N ≥ 2, 0 ≤ P < N) → hour field `P-23/N` (`*/N` when P = 0).
  cron range-with-step is supported by GitHub Actions.
- `24h+P`, `Nd+P`, `1w+P` (0 ≤ P ≤ 23) → P becomes the hour-of-day
  (default remains 0).
- `1h+P` rejected — an every-hour schedule has no phase.

A caller-facing suffix was chosen over baking a fixed hour phase into
`WORKFLOWS` (like the minute offsets) because the phase only matters
when two workflows share an interval — a standing phase would silently
shift refine's daily/weekly slots too, and the spec string in the
comment keeps the retune reproducible from `--show` output alone.

Target cadence after the retune:

| workflow | spec | cron | fires at |
|---|---|---|---|
| pull-card | `1h` | `13 * * * *` | every hour :13 |
| audit-deck | `3h` | `15 */3 * * *` | 00:15, 03:15, … |
| refine-deck | `3h+1` | `45 1-23/3 * * *` | 01:45, 04:45, … |

Refine trails each audit slot by 1 h 30 min, satisfying the ≥1 h
constraint while keeping all three off each other's launch minute.

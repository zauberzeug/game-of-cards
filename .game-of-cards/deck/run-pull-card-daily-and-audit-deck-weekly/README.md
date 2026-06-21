---
title: run-pull-card-daily-and-audit-deck-weekly
summary: "Slowed the autonomous GitHub Actions cadence — pull-card from hourly to daily (03:00 UTC) and audit-deck from daily to weekly (Mondays) — to cut token spend. This cadence was later reversed while headroom was high and is now managed by `scripts/set_cadence.py`; the record stands for the 2026-05-31 slowdown it made."
status: done
stage: null
contribution: low
created: "2026-05-31T03:36:40Z"
closed_at: "2026-05-31T03:37:41Z"
human_gate: none
advances: []
advanced_by: []
tags: [infra, story]
definition_of_done: |
  - [x] MECHANICAL: `.github/workflows/pull-card.yml` cron is daily (`0 3 * * *`), not hourly; the schedule comment matches.
  - [x] MECHANICAL: `.github/workflows/audit-deck.yml` cron is weekly (`0 2 * * 1`), not daily; the schedule comment matches.
  - [x] MECHANICAL: the stale "hourly pull-card" reference in `audit-deck.yml`'s header comment is corrected to "daily".
worker: {who: Rodja Trappe, where: main}
---

# run-pull-card-daily-and-audit-deck-weekly

> Later (2026-06-21): this cadence was deliberately **reversed** while
> spare-token headroom was high — pull-card → hourly, audit-deck → every
> 3h, plus a new refine-deck workflow every 3h, all now managed by
> `scripts/set_cadence.py`. See
> [add-set-cadence-tooling-to-retune-autonomous-workflows](../add-set-cadence-tooling-to-retune-autonomous-workflows/).
> The record below remains accurate for the 2026-05-31 slowdown it made.

Slow the autonomous GitHub Actions cadence: drain the queue once a day
and feed it (audit) once a week, instead of hourly pull / daily audit.

## What changed

| Workflow | Before | After |
|---|---|---|
| `pull-card.yml` | `0 * * * *` (hourly) | `0 3 * * *` (daily, 03:00 UTC) |
| `audit-deck.yml` | `0 2 * * *` (daily) | `0 2 * * 1` (weekly, Mondays 02:00 UTC) |

`audit-deck` is the deck's single queue-feeder, so "refine/audit once a
week" maps to it (there is no separate refine workflow).

## Cadence coordination

`audit-deck` files a card Monday 02:00 UTC; `pull-card` runs daily at
03:00 UTC — one hour later — so the weekly audit's freshly-filed card is
drained the same morning. On the other six days `pull-card` still runs,
draining any human-filed or backlog cards.

"Once a day" is the *trigger* cadence. The existing
`MAX_ITERATIONS`-bounded self-trigger inside `pull-card.yml` is
unchanged: a single daily tick still chains up to 8 fresh-context runs
to clear the backlog in one session, then waits for the next day. (If
the intent was instead one card per calendar day, that would be a
separate change to `MAX_ITERATIONS` / the self-trigger logic — not done
here.)

## Why it matters

The autonomous loops run under `bypassPermissions` and commit/push
without review. Hourly pull + daily audit was a high-throughput cadence;
daily pull + weekly audit reduces churn and cost while still keeping the
queue moving and seeded.

## Out of scope

- `MAX_ITERATIONS` and the self-trigger drain logic — unchanged.
- Model selection (`--model opus`) — unchanged; see
  [float-opus-alias-on-autonomous-github-workflows](../float-opus-alias-on-autonomous-github-workflows/).
- `claude.yml` / `claude-code-review.yml` / `ci.yml` / `release.yml` —
  event-driven, no cron, untouched.

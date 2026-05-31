---
title: run-pull-card-daily-and-audit-deck-weekly
status: active
stage: null
contribution: low
created: "2026-05-31T03:36:40Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [infra, story]
definition_of_done: |
  - [ ] MECHANICAL: `.github/workflows/pull-card.yml` cron is daily (`0 3 * * *`), not hourly; the schedule comment matches.
  - [ ] MECHANICAL: `.github/workflows/audit-deck.yml` cron is weekly (`0 2 * * 1`), not daily; the schedule comment matches.
  - [ ] MECHANICAL: the stale "hourly pull-card" reference in `audit-deck.yml`'s header comment is corrected to "daily".
worker: {who: Rodja Trappe, where: main}
---

# run-pull-card-daily-and-audit-deck-weekly

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

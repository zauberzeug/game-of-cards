---
title: drain-pull-card-queue-per-cron-tick
summary: "The cloud `pull-card` workflow used to pull exactly one card per cron tick, leaving any backlog to drain across many hourly ticks. Switch the workflow to a per-tick drain: each scheduled run pulls cards repeatedly until no `human_gate: none` open cards remain (or the agent stops making progress). Cron cadence relaxed from `*/30` to hourly so a long drain does not overlap itself, and `--max-turns` raised from 200 to 500 so multi-card drains are not truncated mid-card."
status: done
stage: null
contribution: medium
created: 2026-05-09
closed_at: 2026-05-09
human_gate: none
advances: []
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [x] `.github/workflows/pull-card.yml` runs `Skill(pull-card)` in a loop, re-checking `goc --status open --human-gate none --json | jq 'length'` between iterations and stopping when the count is zero or no progress is possible.
  - [x] Workflow cron is `0 * * * *` (hourly), not `*/30 * * * *`.
  - [x] `claude_args` sets `--max-turns 500` (was 200).
  - [x] The pre-LLM `Check autonomous queue` short-circuit is preserved (zero queue → skip Claude step → save tokens).
  - [x] `uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/pull-card.yml'))"` exits zero.
  - [x] `uv run goc validate --quiet` exits zero.
---

# Drain pull-card queue per cron tick

## Summary

`.github/workflows/pull-card.yml` previously fired `Skill(pull-card)`
once per cron tick — one card closed per scheduled run, even when the
queue held a dozen `human_gate: none` open cards. After
[`scheduled-pull-card-completes-a-round`](../scheduled-pull-card-completes-a-round/)
proved the autonomous loop works end-to-end, the natural next step is
to let each tick *drain* the queue rather than nibble at it.

The change is small and surgical: rewrite the prompt so Claude loops
`Skill(pull-card)` until the queue is empty (or no progress is
possible), relax the cron from every-30-minutes to hourly so a long
drain does not get queued behind itself by the existing concurrency
group, and raise `--max-turns` so a multi-card drain is not truncated
mid-card.

## Location

`.github/workflows/pull-card.yml`

## Why drain, not atomic pull

Per-tick atomicity was a deliberate choice when the cloud loop was
unproven (see [`scheduled-pull-card-completes-a-round`](../scheduled-pull-card-completes-a-round/)):
each tick had a small, well-bounded blast radius. Now that a single
tick reliably closes a real card, the bottleneck shifts to *throughput*.
A 12-card backlog used to take 6 hours to drain at 30-minute ticks;
under drain mode it can clear within a single hourly tick, bounded by
the 60-minute job timeout.

The drain stop condition is already encoded in card data: a card is
"non-human" iff `human_gate: none` AND `status: open`. When a card
raises its own gate to `decision`/`session` mid-session, it self-removes
from the drain set — no external bookkeeping needed.

## Why hourly, not every-30-minutes

With per-tick atomicity, overlapping ticks were harmless: the
`concurrency: pull-card-${{ github.ref }}` group serialised them and
each tick pulled one card. Under drain mode, a still-running 45-minute
drain at the next 30-minute tick produces a queued runner that mostly
sits and waits for the first to finish, then likely finds an empty
queue and exits anyway. Hourly aligns the cadence to the actual unit
of work.

## Why bump `--max-turns` from 200 to 500

Each `Skill(pull-card)` round is roughly 10–30 turns (status check,
advance, read, implement, finish, commit). 200 turns covered ~5–10
cards in practice. 500 turns covers ~15–30 cards, which is well past
any realistic backlog. The ceiling exists as a runaway-loop guard, not
a budget — there is no token cost to raising it because it is not hit
on healthy runs.

## What did NOT change

- `timeout-minutes: 60` — unchanged. If the drain runs over, the
  active card stays `status: active` (soft lock) and the next hourly
  run's pull-card preflight respects it.
- The pre-LLM queue-empty short-circuit — unchanged. When the queue is
  already empty at tick start, the Claude step is skipped entirely.
- `--permission-mode bypassPermissions` — unchanged. The cloud runner
  has no human to approve tools, and the runner's GitHub-token
  permissions already bound blast radius.
- The `concurrency` block — unchanged. `cancel-in-progress: false`
  still queues a second tick behind a still-running drain rather than
  killing it.

## Trade-offs vs alternatives

The simplest alternative would have been a shell-level `until count==0`
loop that re-invokes `anthropics/claude-code-action@v1` once per card.
That preserves the per-card cold-start boundary (so a max-turns or
timeout cliff only ever truncates a single card, never an in-progress
multi-card drain). The cost is many cold starts per hour (auth, repo
sync, hook reload), which adds wall time and runner minutes. The
prompt-loop variant chosen here trades worst-case truncation risk for
warm-context throughput. If empirical runs show the truncation hurts
more than the cold-start cost, switch to the shell-loop variant.

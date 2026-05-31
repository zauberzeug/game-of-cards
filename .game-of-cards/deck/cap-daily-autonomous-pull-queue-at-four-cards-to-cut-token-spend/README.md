---
title: cap-daily-autonomous-pull-queue-at-four-cards-to-cut-token-spend
status: active
stage: null
contribution: low
created: "2026-05-31T04:34:11Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [infra, story]
definition_of_done: |
  - [ ] MECHANICAL: `MAX_ITERATIONS` in `.github/workflows/pull-card.yml` is `'4'`, not `'8'`.
  - [ ] MECHANICAL: every comment in `pull-card.yml` that names a specific iteration cap (e.g. "up to 8") matches the new value, or is phrased generically against `MAX_ITERATIONS`.
worker: {who: Rodja Trappe, where: main}
---

# cap-daily-autonomous-pull-queue-at-four-cards-to-cut-token-spend

Halve the per-day token budget of the autonomous loop by lowering the
self-trigger cap in `pull-card.yml` from 8 to 4.

## What changed

| Setting | Before | After |
|---|---|---|
| `MAX_ITERATIONS` (`pull-card.yml`) | `'8'` | `'4'` |

## Why it matters

The daily 03:00 UTC cron fires `iteration=1`, which self-chains via
`workflow_dispatch` up to `MAX_ITERATIONS` fresh-context runs to drain
the queue in one session. Each iteration is a full Opus agent run under
`bypassPermissions` — the dominant daily token cost of the autonomous
loop. Capping at 4 roughly halves the worst-case daily spend while still
clearing a small backlog each morning; anything beyond 4 cards simply
rolls to the next day's tick.

This is the follow-up the sibling card
[run-pull-card-daily-and-audit-deck-weekly](../run-pull-card-daily-and-audit-deck-weekly/)
explicitly deferred ("a separate change to `MAX_ITERATIONS` / the
self-trigger logic — not done here").

## Out of scope

- The cron cadence (daily pull / weekly audit) — unchanged.
- The self-trigger / re-trigger logic itself — only the cap value moves.
- Model selection (`--model opus`) and `--max-turns` — unchanged.

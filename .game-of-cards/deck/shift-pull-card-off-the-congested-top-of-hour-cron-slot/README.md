---
title: shift-pull-card-off-the-congested-top-of-hour-cron-slot
summary: "Move pull-card's scheduled cron minute from `:00` to `:13` to cut GitHub Actions schedule-dispatch delay. Minute `:00` is the most congested slot on GitHub's shared scheduler queue — the old `0 3 * * *` cron dispatched ~85-90 min late — and sibling workflows already dodge it; this moves pull-card off the top of the hour."
status: done
stage: null
contribution: low
created: "2026-06-21T07:16:43Z"
closed_at: "2026-06-21T07:18:34Z"
human_gate: none
advances: []
advanced_by: []
tags: [infra, story]
definition_of_done: |
  - [x] MECHANICAL: `scripts/set_cadence.py` WORKFLOWS["pull"] minute offset is `13` (was `0`); the docstring and the `tune-cadence` SKILL.md offset note both say `:13`.
  - [x] MECHANICAL: `.github/workflows/pull-card.yml` cron is `13 * * * *` with its `# cadence:` comment showing offset `:13`, applied via the script (an idempotent re-run is a no-op).
  - [x] MECHANICAL: `test_set_cadence` + `goc validate` + `sync --check` are green (suite unchanged modulo the sandbox-only interactive-rebase test); the parent card `add-set-cadence-tooling-to-retune-autonomous-workflows` is amended with a `log.md` forward pointer.
worker: {who: Rodja Trappe, where: main}
---

# shift-pull-card-off-the-congested-top-of-hour-cron-slot

Move pull-card's scheduled minute from `:00` to `:13` to cut GitHub
Actions schedule-dispatch delay.

## Why

GitHub's `schedule` trigger is a best-effort job on a queue shared by
every repo on GitHub, and minute `:00` is the most congested slot —
a huge fraction of all crons fire at the top of the hour, so GitHub's
scheduler drains that backlog late. This repo's old daily `0 3 * * *`
cron consistently dispatched ~85–90 min late (runs landed ~04:28).
GitHub's own docs recommend scheduling off the top of the hour to
reduce the chance of delay.

The sibling offsets chosen in
[add-set-cadence-tooling-to-retune-autonomous-workflows](../add-set-cadence-tooling-to-retune-autonomous-workflows/)
already dodge this for audit-deck (`:15`) and refine-deck (`:45`);
pull-card was left at `:00`, the worst slot. This card moves it to
`:13`.

## What changed

| Workflow | Before | After |
|---|---|---|
| `pull-card.yml` | `0 * * * *` (hourly at :00) | `13 * * * *` (hourly at :13) |

Still hourly — just shifted off the congested minute. The offset is a
fixed constant in `set_cadence.py`'s `WORKFLOWS` table, so the change
is one literal plus a re-run of the script; cadence interval is
unchanged.

## Out of scope

- Audit/refine offsets (`:15` / `:45`) — already off the top of the hour.
- The interval (hourly) and `MAX_ITERATIONS` — unchanged.
- Guaranteed timing — GitHub cron can't provide it; a self-hosted timer
  would be a separate decision.

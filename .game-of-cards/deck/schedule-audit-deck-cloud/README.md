---
title: schedule-audit-deck-cloud
summary: "Run `Skill(audit-deck)` from GitHub Actions on a daily cron at 02:00 UTC so the queue is fed without a human session staying open. Mirrors `.github/workflows/pull-card.yml` (the drainer); this is the feeder. Audit-deck files one new card per run from emergent codebase observations; the next hourly `pull-card` tick then drains it. Pairs naturally: feed nightly, drain hourly."
status: done
stage: null
contribution: medium
created: 2026-05-09
closed_at: 2026-05-09
human_gate: none
advances: []
advanced_by: []
tags: [infra]
definition_of_done: |
  - [x] `.github/workflows/audit-deck.yml` exists and runs `Skill(audit-deck)` via `anthropics/claude-code-action@v1` on a daily cron at `0 2 * * *` (02:00 UTC).
  - [x] Workflow supports `workflow_dispatch` for manual triggers.
  - [x] Workflow grants `id-token: write` (OIDC for the Claude action) plus `contents: write`, `pull-requests: write`, `issues: write` so the agent can commit and push the new card.
  - [x] Workflow has a `concurrency` block scoped to the ref so manual + scheduled triggers do not overlap.
  - [x] Prompt instructs the agent to run `Skill(audit-deck)` once, file at most one new card, and translate bare `goc ...` commands to `uv run goc ...` (this repo is the source tree for `goc`).
  - [x] `claude_args` sets `--max-turns 200` and `--permission-mode bypassPermissions`, matching the established cloud pattern.
  - [x] `uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/audit-deck.yml'))"` exits zero.
  - [x] `uv run goc validate --quiet` exits zero.
worker: {who: Rodja Trappe, where: main}
---

# Schedule audit-deck in cloud

## Summary

The autonomous loop has two halves:

- **Drain** — `.github/workflows/pull-card.yml` runs hourly and pulls
  `human_gate: none` open cards until the queue is empty.
- **Feed** — `Skill(audit-deck)` files one new card per run from
  emergent codebase observations (defect, doc drift, derivation gap,
  architectural ugliness).

Today the feeder runs only when a human invokes it locally. The drain
side is fully cloud-automated; the feed side is not. So the cloud
worker eventually starves: hourly drain ticks find an empty queue and
exit, while real defects accumulate uncommitted in the codebase.

This card adds the feeder workflow. Daily 02:00 UTC cron triggers
`Skill(audit-deck)`; the skill files one card and commits it; the next
hourly `pull-card` tick drains it. The two workflows together turn the
codebase into a self-feeding queue.

## Location

New file: `.github/workflows/audit-deck.yml`. Reference for shape and
conventions: `.github/workflows/pull-card.yml`.

## Why daily, not weekly

The shipped `pull-card` SKILL.md mentions `/schedule audit-deck weekly
— keeps the queue fed; the pull-principle requires something to pull.`
Weekly is the conservative default for a queue that drains slowly.
With drain-mode hourly pull-card, the queue can clear ~10 cards per
day; a weekly feeder would leave 6 days of empty drain ticks per
cycle. Daily aligns the feeder cadence to the drain capacity.

If the daily feed produces low-signal cards (audits with thin findings,
duplicates of recently-disproved entries), step the cron back to
`0 2 * * 1` (Mondays) without rewriting the workflow.

## Why 02:00 UTC

GitHub Actions cron is UTC. 02:00 UTC is off-peak globally:

- 03:00 / 04:00 Berlin (CET/CEST) — pre-dawn, no human session likely.
- 21:00 / 22:00 New York (EST/EDT) — late evening.
- 10:00 / 11:00 Tokyo (JST) — mid-morning.

The cron is not load-bearing; if the user wants exact-2am-local-time
they can adjust the offset.

## Why one card per run, not many

`Skill(audit-deck)` is by design one-defect-per-invocation (Phase 3 of
the skill body: "For each confirmed candidate" — typically one).
Filing more than one card per scheduled run would mean either looping
the skill (raises the question "when does it stop?") or letting the
skill itself widen its scope (which the existing skill body
deliberately bounds). Daily × one card = ~30 cards/month of audit-fed
work, well above current drain throughput.

## What the prompt must say

Cloud-mode quirks to encode in the prompt:

1. The agent is in a fresh checkout; it has no human to escalate to.
2. This repo is the source tree for `goc`, so bare `goc ...` calls in
   the skill body must be translated to `uv run goc ...`.
3. The skill itself handles commit + push (see `Phase 4 — Commit` in
   the skill body), so the prompt should not duplicate commit
   instructions.

## Trade-offs vs alternatives

- **Manual `gh workflow run audit-deck` instead of cron.** Removes the
  daily token spend but requires a human in the loop, which defeats
  the autonomous-loop premise.
- **Trigger from `pull-card.yml` when the queue empties.** Tighter
  coupling and harder to reason about (drain runs that empty the queue
  would each trigger an audit, multiplying token cost). A separate
  schedule keeps the feeder rate-limited at the cron level.
- **Run audit-deck inline at the top of `pull-card.yml`.** Couples
  feed cadence to drain cadence (hourly audit is too noisy). Separate
  workflow keeps the cadences independent.

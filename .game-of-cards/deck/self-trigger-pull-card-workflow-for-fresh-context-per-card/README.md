---
title: self-trigger-pull-card-workflow-for-fresh-context-per-card
summary: "Restructure pull-card.yml so each iteration is its own GitHub Actions run with a fresh context, chained via gh workflow run self-trigger."
status: done
stage: null
contribution: medium
created: 2026-05-09
closed_at: 2026-05-09
human_gate: none
advances:
  - pull-card-self-trigger-needs-empirical-verification
advanced_by: []
tags: [infra, story]
definition_of_done: |
  - [x] `pull-card.yml` invokes `claude-code-action@v1` exactly once per workflow run (no in-prompt loop).
  - [x] After the action step, the workflow re-checks the queue and self-triggers via `gh workflow run pull-card.yml -f iteration=<n+1>` if cards remain and `iteration < MAX_ITERATIONS`.
  - [x] `MAX_ITERATIONS=8` env var caps the chain length per cron tick.
  - [x] `permissions.actions: write` added so the default `GITHUB_TOKEN` can dispatch the next run.
  - [x] `--max-turns` per iteration set to 120 (down from 500 for the whole drain — still generous for one card).
  - [x] `concurrency.group + cancel-in-progress: false` retained so chains serialize and parallel cron firings queue safely.
  - [x] Workflow prompt rewritten: the action runs `Skill(pull-card)` exactly once and exits; the harness handles iteration.
worker: {who: Rodja Trappe, where: main}
---

# self-trigger-pull-card-workflow-for-fresh-context-per-card

The current `pull-card.yml` runs `anthropics/claude-code-action@v1`
once and tells the agent in the prompt to loop: "Run `Skill(pull-card)`,
re-check the queue, repeat until empty." That single CLI session
accumulates context across every card pulled — body reads, file edits,
slash-command output, commits — so by card 5 the model is operating on
hundreds of thousands of tokens of haystack with degraded fidelity.
Claude Code's auto-compaction is reactive (fires near the 1M ceiling,
not at a configurable threshold) and lossy (summarization, not reset).

The right shape is one `claude-code-action@v1` run per card, with the
loop at the harness layer. Each run gets a clean process, fresh OAuth
session, and an unbloated context budget.

## Mechanism

GitHub Actions exempts `workflow_dispatch` and `repository_dispatch`
from its no-cascading-triggers rule for the default `GITHUB_TOKEN`
(see [docs](https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication#using-the-github_token-in-a-workflow)).
A step inside `pull-card.yml` can call `gh workflow run pull-card.yml`
and the next run starts cleanly. The existing `concurrency.group`
serializes chains so iterations never run in parallel.

## Iteration counter as killswitch

Each self-triggered run passes `iteration=<n+1>`. Cron-triggered runs
default to `iteration=1`. The re-trigger step's `if:` clause checks
`iteration < MAX_ITERATIONS`, so a stuck card cannot spin a chain
indefinitely. If the cap is hit and the queue is still non-empty,
cron picks up next tick and starts a fresh chain. Chronic cap-hitting
is a paged signal that the queue is filling faster than pull-card can
drain — useful diagnostic, not a runaway.

## Out of scope

- `audit-deck.yml` keeps its current single-run shape — it files exactly
  one card per invocation by skill contract, so there's no
  multi-iteration context bloat to solve there.
- The cron schedule stays hourly. Tighter cron makes sense only if the
  chain consistently caps at `MAX_ITERATIONS`, which would mean the
  queue is growing faster than projected. Revisit then.

## References

- [`secrets.GITHUB_TOKEN` triggering workflows](https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication#using-the-github_token-in-a-workflow) — `workflow_dispatch` and `repository_dispatch` are the documented exceptions to the no-cascade rule.
- Sibling card: `pin-opus-on-autonomous-github-workflows` (closed 2026-05-09) pinned the model; this card pins the *shape* of how that model is invoked.

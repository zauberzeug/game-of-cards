---
title: autonomous-pull-card-runs-stop-at-the-turn-cap-before-pushing-their-work
summary: "Since 2026-10-15 nearly every scheduled or chained pull-card run ends with 'Reached maximum number of turns (120)', and runs that had not pushed yet lose their work (2026-10-21: a new card plus fix; 2026-10-22: a claim left stranded). Where the turns go is unmeasured, so whether to raise the cap, lower the effort, push earlier or stop a Stop-hook loop needs a decision backed by a turn breakdown."
status: open
stage: null
contribution: high
created: "2026-10-22T06:03:27Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] EMPIRICAL: a turn breakdown of at least three of the failed runs below (skill loads, tool calls per DoD step, Stop-hook reminder turns, audit fallback after the pick) is recorded in log.md, and it confirms or refutes the Stop-hook hypothesis
  - [ ] PROCESS: the decision below is recorded via goc decide
  - [ ] MECHANICAL: the chosen change lands in `.github/workflows/pull-card.yml` and/or the pull-card skill (a workflow edit needs a human commit — the bot token cannot push `.github/workflows/`)
  - [ ] EMPIRICAL: the next five scheduled pull-card runs end without `Reached maximum number of turns`, or the remaining failures are explained in log.md
  - [ ] PROCESS: `uv run goc validate` passes
---

# Autonomous pull-card runs stop at the turn cap before pushing their work

## Location

- `.github/workflows/pull-card.yml` — `claude_args: --max-turns 120 --permission-mode bypassPermissions --model opus --effort max`.
- `goc/templates/skills/pull-card/SKILL.md` — the round the agent runs inside that budget.
- `goc/templates/hooks/pattern_generalization_check.py` — the Stop hook that asks for a generalization after code-mutating turns (enabled in this repo's `.game-of-cards/config.yaml`).

## What's broken

The workflow's job annotation for almost every run since 2026-10-15 is `Action failed with error: Claude execution failed: Reached maximum number of turns (120)`:

| Run | Date | Event | What the run had done when it stopped |
|---|---|---|---|
| 38852198476 | 2026-10-16 | chained dispatch | max turns |
| 39004224804 | 2026-10-17 | chained dispatch | max turns |
| 39097105013 | 2026-10-18 | schedule | filed, fixed and closed a card (6c5cb9f2), then kept going until the cap |
| 39369677390 | 2026-10-20 | schedule | filed a card (2cfb1575), then the cap |
| 39544258204 | 2026-10-21 | schedule | committed a new card and an `install.py` fix locally (98b1a58c), never pushed — the work is lost |
| 39722531484 | 2026-10-22 | schedule | claimed `runtime-hooks-fire-in-repos-that-never-opted-in` (c9406ad6), then the cap; the claim stayed `active` until a human released it |

(2026-10-19 failed on the org spend limit instead, not on turns.)

Two consequences: a run that ends at the cap before its push loses everything it did, and a run that ends after a claim strands the card at `active`, outside every queue (the failure path PR #11 named: nothing writes when a run dies mid-flight).

## Hypotheses (unmeasured)

1. **Stop-hook loop.** The pattern-generalization Stop hook prompts after every code-mutating turn. In an unattended run nothing answers "no", so the agent keeps filing or extending generalization cards; run 39097105013 closed its card and still ran to the cap.
2. **Audit fallback.** When the ready queue is thin, the pull-card skill falls through to an audit, which files *and* works a new card in the same budget (2026-10-18, -20, -21 all filed new cards).
3. **Skill weight.** `--effort max` plus several large skill loads per round (pull-card, create-card, finish-card, card-schema) may simply not fit 120 turns for a TDD card with mirror sync.

## Decision required

Which change, after the turn breakdown (DoD 1) says where the turns go?

- **A. Raise `--max-turns`** (e.g. 200): cheapest edit; a run that would finish now finishes, but a looping run burns more budget before it stops — relevant while the org spend limit is being hit.
- **B. Stop the loop at its source**: if hypothesis 1 holds, make the Stop hook quiet in unattended runs (or after a generalization was filed once) instead of buying more turns.
- **C. Push early**: have the pull-card skill commit and push the claim, the fix and the closure as separate steps, so a capped run loses at most its last step; pair it with a stale-claim release.
- **D. Narrow the round**: forbid the audit fallback inside pull-card runs (audit-deck has its own weekly workflow).

These are not exclusive; the breakdown should pick the smallest set that works.

## Why it matters

The pull-card workflow is the project's main autonomous throughput. With the queue fix of 2026-10-22 (`goc --ready` gating), it now launches only when a card is pullable, so a capped run is no longer wasted on an empty queue — but it still wastes the run whenever the round does not fit, and it can strand the one card it picked.

Related: [scheduled-pull-card-completes-a-round](../scheduled-pull-card-completes-a-round/) (closed; the May version of this problem at `--max-turns 40`), [run-autonomous-agent-workflows-at-max-effort](../run-autonomous-agent-workflows-at-max-effort/), [make-pattern-generalization-stop-hook-opt-in](../make-pattern-generalization-stop-hook-opt-in/). The finding of run 39544258204 (`goc install`'s "Next:" hint asks for a phrase no skill handles — "expand the deck") was lost with that run and is not on main; re-file it if it still reproduces.

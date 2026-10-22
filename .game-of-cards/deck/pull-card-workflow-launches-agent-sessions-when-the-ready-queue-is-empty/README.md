---
title: pull-card-workflow-launches-agent-sessions-when-the-ready-queue-is-empty
summary: "`.github/workflows/pull-card.yml` gated the LLM agent step on `goc --status open --human-gate none --json | jq length`, but the `Skill(pull-card)` it launches selects via `goc --ready`, which additionally excludes cards with an active `waiting_on`/`waiting_until` overlay. When only impeded cards remained, the workflow counted >0, launched a full agent session that found nothing to pull, and the identical post-check re-triggered it — up to MAX_ITERATIONS wasted sessions per cron tick. Fixed: both count steps now count `goc --ready --json`, landed together with the fail-closed pipefail patch of the sibling card."
status: done
stage: null
contribution: high
created: "2026-07-23T01:11:06Z"
closed_at: "2026-10-22T03:22:19Z"
human_gate: none
advances:
  - extend-pull-readiness-coupling-invariant-to-the-board-not-ready-predicate
advanced_by: []
tags: [bug, infra, meta-fix]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — the workflow's queue-count steps no longer use the `--status open --human-gate none` predicate that diverges from `goc --ready`
  - [x] MECHANICAL: both count sites in `.github/workflows/pull-card.yml` (`Check autonomous queue`, `Re-check queue`) count `uv run goc --ready --json | jq 'length'`, and the printed label says "ready" instead of "Pullable cards (status=open, human_gate=none)" — requires a HUMAN commit (the bot's GITHUB_TOKEN cannot modify `.github/workflows/`)
  - [x] PROCESS: cross-referenced as a fourth pull-readiness copy on [extend-pull-readiness-coupling-invariant-to-the-board-not-ready-predicate](../extend-pull-readiness-coupling-invariant-to-the-board-not-ready-predicate/)
  - [x] PROCESS: `uv run goc validate` passes
worker: {who: Rodja Trappe, where: main}
---

# pull-card workflow launches agent sessions when the ready queue is empty

## Location

`.github/workflows/pull-card.yml:63` (`Check autonomous queue`) and the
identical re-check at line 106 (`Re-check queue`):

```bash
count="$(uv run goc --status open --human-gate none --json | jq 'length')"
```

The first count gates the `Pull one card` agent step
(`if: steps.queue.outputs.count != '0'`, line 71); the second gates the
`Re-trigger workflow if cards remain` step (lines 111–113), which
dispatches the workflow again up to `MAX_ITERATIONS: '4'`.

## What's broken

The workflow's "pullable" predicate is `status: open ∧ human_gate: none`.
But the thing it launches — `Skill(pull-card)` — selects work via
`goc --ready` (`goc/templates/skills/pull-card/SKILL.md`), i.e.
`card_is_ready` in `goc/engine.py`, which the skill body itself defines as:

> `--ready` filters to `status: open` ∧ `human_gate: none` ∧ **no active
> `waiting_on` overlay**

A card parked with `goc wait --reason external` (or deferred with a
future `waiting_until`) stays `open` at gate `none`, so the workflow
counts it as pullable while the picker inside the agent session refuses
it. Consequence when only impeded cards remain:

1. The pre-check counts >0 → a full LLM agent session launches.
2. The session runs `goc --ready`, finds an empty queue, and (per the
   pull-card skill) falls through to an audit or exits.
3. The post-check counts the same impeded cards >0 → the workflow
   **re-triggers itself**, up to 4 iterations — every cron tick,
   indefinitely, until the overlays clear.

## Empirical evidence

Live on this repo's own deck at filing time (see `reproduce.py` for the
hermetic scratch-deck version):

```
$ uv run goc --status open --human-gate none --json | jq length
3
$ uv run goc --ready --json | jq length
0
```

The three counted cards (`openclaw-subagent-plugin-tools-alsoallow-ignored`,
`blocked-status-conflates-dependency-external-wait-and-deferral`,
`remove-blocked-from-status-enum-and-migrate-existing-cards`) all carry
active `waiting_on: external`/`deferred` overlays. The audit session
that filed this card is itself one of the falsely-launched runs.

`reproduce.py` builds a scratch deck with one open, gate-none,
`waiting_on: external` card and prints the two counts (workflow
predicate: 1, ready: 0), then checks whether `pull-card.yml` still uses
the drifting predicate. It exits non-zero today and zero after the fix.

## Why it matters

Each false launch is a full `claude-code-action` session (up to 120
turns) that can do no queue work. With the 12h cron and 4 chained
iterations this wastes up to 8 agent sessions/day whenever the residual
queue is all-impeded — the exact steady state a well-drained deck
converges to.

This is also a fourth hand-rolled copy of the pull-readiness predicate,
outside the engine and outside the coupling guard
(`tests/test_scheduler_workable_predicate_coupling.py`) — see
[extend-pull-readiness-coupling-invariant-to-the-board-not-ready-predicate](../extend-pull-readiness-coupling-invariant-to-the-board-not-ready-predicate/)
(the board copy drifted the same way) and
[waiting-impedes-callers-reimplement-the-terminal-status-liveness-gate-and-drift](../waiting-impedes-callers-reimplement-the-terminal-status-liveness-gate-and-drift/)
(the overlay-axis sibling family). The shell fix below removes the
reimplementation instead of patching it: the workflow should ask the
engine the exact question the picker asks.

## Fix

Applied: both count sites in `.github/workflows/pull-card.yml`
(`Check autonomous queue`, `Re-check queue`) now ask the engine the
exact question the picker asks:

```bash
count="$(uv run goc --ready --json | jq 'length')"
```

with the labels `Ready cards (goc --ready)` and `Remaining ready
cards`. `reproduce.py` exits zero: the scratch deck's impeded card
counts 1 under the old predicate and 0 under `--ready`, and the
workflow no longer uses the old predicate.

It landed together with the sibling's fail-closed patch
([pull-card-workflow-launches-agents-when-goc-itself-fails-to-count-the-queue](../pull-card-workflow-launches-agents-when-goc-itself-fails-to-count-the-queue/)):
the `--ready` line alone keeps the unguarded pipe, so a failing `goc`
would still leave an empty count that launches the agent. The shared
`pull-card-yml.patch` adds a workflow-level `shell: bash` (pipefail) and
`count > 0` gates.

The fix needed a human commit: GitHub rejects pushes from the
workflow's token that modify `.github/workflows/` ("refusing to allow a
GitHub App to create or update workflow ... without `workflows`
permission"; documented first-hand on
[pull-card-workflow-skips-pre-commit-so-bot-commits-bypass-goc-validate](../pull-card-workflow-skips-pre-commit-so-bot-commits-bypass-goc-validate/)).

## Decision

*Resolved 2026-10-22T03:17:04Z:* Count the queue with goc --ready in both pull-card.yml count steps, landed together with the fail-closed patch of the pipefail sibling

*Reasoning:* Maintainer approved switching pull-card.yml to goc --ready in a human session on 2026-10-22; the fix was already determined and only needed a human commit, since the bot token cannot push .github/workflows/


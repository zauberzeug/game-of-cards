---
title: pull-card-workflow-launches-agents-when-goc-itself-fails-to-count-the-queue
summary: "UNVERIFIED. pull-card.yml counts the queue with count=$(uv run goc ... --json | jq 'length') under GitHub's default bash -e without pipefail, so when goc exits non-zero jq sees empty input, exits 0, and the count is empty. The step succeeds, the condition count != '0' holds, and the Opus agent session launches and re-triggers, failing open exactly when the engine is broken."
status: open
stage: null
contribution: medium
created: "2026-09-28T01:38:32Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, unverified]
definition_of_done: |
  - [ ] TDD: a reproduce.py runs the `Check autonomous queue` step body under `bash -e` with a `goc` stand-in that exits non-zero, and asserts the step fails (or reports a zero count) instead of emitting an empty count that launches the agent — or the run disproves the hypothesis and the card flips to `disproved`
  - [ ] MECHANICAL: both count sites in `.github/workflows/pull-card.yml` (`:63`, `:107`) fail closed when `goc` fails — `shell: bash` (which adds `-o pipefail`) or an explicit exit-status check — and the launch / re-trigger conditions treat a non-numeric count as "do not launch" (requires a HUMAN commit — the bot's GITHUB_TOKEN cannot modify `.github/workflows/`)
  - [ ] MECHANICAL: drop the `unverified` tag once reproduce.py lands; cross-check the fix against `pull-card-workflow-launches-agent-sessions-when-the-ready-queue-is-empty`'s proposed count line, which keeps the same pipe
---

# The pull-card workflow launches agents when `goc` itself fails to count the queue

> **UNVERIFIED.** Surfaced by an audit hunter on the repo-scripts-and-CI
> seam on 2026-09-28. The filing agent re-read the citations and
> re-demonstrated the shell behavior. No `reproduce.py` was written this
> round; the falsification recipe is below.

## Location

- `.github/workflows/pull-card.yml:63` (`Check autonomous queue`) and
  `:107` (`Re-check queue`):
  `count="$(uv run goc --status open --human-gate none --json | jq 'length')"`.
- `:66`: `if [ "$count" -eq 0 ]; then`.
- `:71`: `if: steps.queue.outputs.count != '0'`, which gates the agent
  step.
- `:113-114`: `steps.post.outputs.count != '0' && …`, which gates the
  self re-trigger.
- No workflow sets `shell:` or `defaults:`. GitHub runs an unspecified
  shell as `bash -e {0}`. Only an explicit `shell: bash` adds
  `-o pipefail`.

## Hypothesis

When `goc` exits non-zero, the step does not notice. Examples: an engine
regression pushed by a pull-card session, a renamed flag, or a card whose
bytes are not valid UTF-8. The pipe's status is `jq`'s, and `jq` on empty
input prints nothing and exits 0. So `count` is empty, the step succeeds,
and `'' != '0'` launches the Opus max-effort agent session. The
re-trigger step then does the same, up to `MAX_ITERATIONS`.

The filing agent reproduced the shell half directly:

```
$ bash -e -c 'count="$(false | jq length)"; echo "count=[$count]"; if [ "$count" -eq 0 ]; then echo empty; fi; echo step_ok'; echo "rc=$?"
count=[]
bash: line 1: [: : integer expression expected
step_ok
rc=0
```

The hunter ran the step body with a flag `goc` rejects and with a
non-UTF-8 card. Both produced `count=[]` and step rc=0, and the launch
condition evaluated to LAUNCH. Under `bash -eo pipefail` the same body
failed with rc=1.

The gate exists to skip agent sessions when there is nothing to do. It
fails open exactly when the engine is broken, which is also when an
autonomous session is least able to make progress. Bot pushes do not
trigger CI (see
[autonomous-pushes-do-not-trigger-ci-so-the-regression-suite-gates-nothing](../autonomous-pushes-do-not-trigger-ci-so-the-regression-suite-gates-nothing/)),
so nothing else stops the loop either.

## Why deferred

The citations are confirmed and the shell semantics re-demonstrated. No
`reproduce.py` is committed this round. The fix edits
`.github/workflows/`, which the autonomous bot cannot commit.

Related:
[pull-card-workflow-launches-agent-sessions-when-the-ready-queue-is-empty](../pull-card-workflow-launches-agent-sessions-when-the-ready-queue-is-empty/)
(open) fixes *what* the gate counts, and its proposed line
`count="$(uv run goc --ready --json | jq 'length')"` keeps this failure
mode. Land both in one workflow edit. `ci.yml:53`
(`goc --help | head -5`) has the same unguarded-pipe shape.

## Falsification recipe

Put a `goc` stand-in that exits 2 first on `PATH`, then run the step body
under `bash -e`. If the step exits non-zero, the hypothesis is disproved.
It is also disproved if `count` ends up `0`.

Surfaced by: general-purpose audit hunter (repo scripts and CI
workflows), 2026-09-28.

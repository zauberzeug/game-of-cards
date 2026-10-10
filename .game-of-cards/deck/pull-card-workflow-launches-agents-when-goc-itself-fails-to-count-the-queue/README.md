---
title: pull-card-workflow-launches-agents-when-goc-itself-fails-to-count-the-queue
summary: "pull-card.yml counts the queue with count=$(uv run goc ... --json | jq 'length') under GitHub's default bash -e, which has no pipefail. When goc exits non-zero, jq sees empty input and exits 0, so the step succeeds with an empty count and the count != '0' gates launch the Opus agent session and the self re-trigger. Confirmed: reproduce.py shows both count steps failing open, and a real engine crash does the same. pull-card-yml.patch fixes it together with the sibling --ready card. Parked at session because only a human commit can change .github/workflows/."
status: open
stage: null
contribution: medium
created: "2026-09-28T01:38:32Z"
closed_at: null
human_gate: session
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: a reproduce.py runs the `Check autonomous queue` step body under `bash -e` with a `goc` stand-in that exits non-zero, and asserts the step fails (or reports a zero count) instead of emitting an empty count that launches the agent — or the run disproves the hypothesis and the card flips to `disproved`
  - [ ] MECHANICAL: both count sites in `.github/workflows/pull-card.yml` (`:63`, `:107`) fail closed when `goc` fails — `shell: bash` (which adds `-o pipefail`) or an explicit exit-status check — and the launch / re-trigger conditions treat a non-numeric count as "do not launch" (requires a HUMAN commit — the bot's GITHUB_TOKEN cannot modify `.github/workflows/`)
  - [x] MECHANICAL: drop the `unverified` tag once reproduce.py lands; cross-check the fix against `pull-card-workflow-launches-agent-sessions-when-the-ready-queue-is-empty`'s proposed count line, which keeps the same pipe
worker: {who: "claude[bot]", where: main}
---

# The pull-card workflow launches agents when `goc` itself fails to count the queue

> **Confirmed 2026-10-10.** `reproduce.py` runs both count steps the way
> GitHub would, and both fail open. A real engine crash fails open too.
> The fix is `pull-card-yml.patch`, verified on a scratch copy. The card
> is parked at `session` because only a human commit can change
> `.github/workflows/` (see "Why the session gate").

## Location

- `.github/workflows/pull-card.yml:63` (`Check autonomous queue`) and
  `:107` (`Re-check queue`):
  `count="$(uv run goc --status open --human-gate none --json | jq 'length')"`.
- `:66`: `if [ "$count" -eq 0 ]; then`.
- `:71`: `if: steps.queue.outputs.count != '0'`, which gates the agent
  step.
- `:113-114`: `steps.post.outputs.count != '0' && …`, which gates the
  self re-trigger. `:125-126` gates the iteration-cap notice the same
  way.
- No workflow sets `shell:` or `defaults:`. GitHub runs an unspecified
  shell as `bash -e {0}`. Only an explicit `shell: bash` adds
  `-o pipefail`.

## Defect

When `goc` exits non-zero, the step does not notice. Causes include an
engine regression pushed by a pull-card session, a renamed flag, or a
card whose bytes are not valid UTF-8. The pipe's status is `jq`'s, and
`jq` on empty input prints nothing and exits 0. So `count` is empty, the
step succeeds, and `'' != '0'` launches the Opus max-effort agent
session. The re-trigger step then does the same, up to `MAX_ITERATIONS`.
The shell half fits in one line:

```
$ bash -e -c 'count="$(false | jq length)"; echo "count=[$count]"; if [ "$count" -eq 0 ]; then echo empty; fi; echo step_ok'; echo "rc=$?"
count=[]
bash: line 1: [: : integer expression expected
step_ok
rc=0
```

The gate exists to skip agent sessions when there is nothing to do. It
fails open exactly when the engine is broken, which is also when an
autonomous session is least able to make progress. Bot pushes do not
trigger CI (see
[autonomous-pushes-do-not-trigger-ci-so-the-regression-suite-gates-nothing](../autonomous-pushes-do-not-trigger-ci-so-the-regression-suite-gates-nothing/)),
so nothing else stops the loop either.

## Evidence

`reproduce.py` reads `pull-card.yml` with goc's own `yaml_lite`. It
finds every step whose output a later `if:` reads (`queue` and `post`)
and runs each body under the shell GitHub would pick: the step's
`shell:`, else the job's then the workflow's `defaults.run.shell`, else
the runner default `bash -e {0}`. `uv` and `goc` stand-ins go first on
`PATH`. Two controls (`[]` gives 0, a two-card array gives 2) show the
body is run faithfully. Then the stand-ins exit 2. At HEAD:

```
[OPEN]   `Check autonomous queue` (steps.queue.outputs.count) under `bash -e {0}`: exit 0, count=''; the steps reading it are not skipped and see count=''
[OPEN]   `Re-check queue` (steps.post.outputs.count) under `bash -e {0}`: exit 0, count=''; the steps reading it are not skipped and see count=''
[FAIL] 2 of 2 count step(s) fail open: ...
```

It exits 1 while the defect is present, 0 once every count step fails
closed, and 2 when the workflow shape or a control does not hold.

The real engine fails the same way. In a scratch deck, a card holding
one Latin-1 byte (`caf\xe9`) makes `goc --status open --human-gate none
--json` exit 1 on a `UnicodeDecodeError`. The live `Check autonomous
queue` body, run against that engine under `bash -e`, printed
`Pullable cards (status=open, human_gate=none): ` and `[: : integer
expression expected`, wrote `count=` to `GITHUB_OUTPUT`, and exited 0.
Under `bash --noprofile --norc -eo pipefail` the same body exited 1 and
wrote nothing.

## Fix

`pull-card-yml.patch`, in this directory, is a single workflow edit. It
lands this card and
[pull-card-workflow-launches-agent-sessions-when-the-ready-queue-is-empty](../pull-card-workflow-launches-agent-sessions-when-the-ready-queue-is-empty/)
together:

1. **Fail closed.** A workflow-level `defaults: run: shell: bash` gives
   every `run:` step `-o pipefail`. A failing `goc` now fails the count
   step, and the implicit `success()` skips the agent launch and the
   re-trigger. The job turns red, which is the signal a broken engine
   should send.
2. **A non-numeric count never launches.** The three gates compare
   `count > 0` instead of `count != '0'`. GitHub coerces a string to a
   number for `>`: the empty string becomes 0, anything non-numeric
   becomes NaN, and a relational comparison with NaN is always false.
   So a missing or garbled count cannot launch the agent, even if a
   later edit loses the pipefail.
3. **Count what the picker pulls.** `goc --ready --json` replaces
   `--status open --human-gate none --json`, with matching labels. This
   is the sibling card's fix.

Cross-check against the sibling: its proposed line alone,
`count="$(uv run goc --ready --json | jq 'length')"`, still fails open
under `reproduce.py`, so the two fixes must land together. With the
patch applied to a scratch copy, `reproduce.py --workflow <copy>` reports
both steps `[CLOSED]` and exits 0. The sibling's predicate check also
passes on that copy: no `--status open --human-gate none --json` is
left, and both sites read `--ready --json`. Other fail-closed shapes pass
`reproduce.py` too, if a reviewer prefers one: a per-step `shell: bash`,
a job-level `defaults`, `set -o pipefail` in each body, or an explicit
`json="$(uv run goc --ready --json)"` exit-status check.

Out of scope: `ci.yml:53` (`goc --help | head -5`) has the same
unguarded pipe. But `goc --version` on the line above already fails the
step when the console script is missing, so only a help-rendering crash
slips through.

## Why the session gate

GitHub rejects pushes from the workflow's token that modify
`.github/workflows/` ("refusing to allow a GitHub App to create or
update workflow ... without `workflows` permission", recorded first-hand
on
[pull-card-workflow-skips-pre-commit-so-bot-commits-bypass-goc-validate](../pull-card-workflow-skips-pre-commit-so-bot-commits-bypass-goc-validate/)),
so the bot cannot land the patch. A human session:

1. `git apply .game-of-cards/deck/pull-card-workflow-launches-agents-when-goc-itself-fails-to-count-the-queue/pull-card-yml.patch`
2. Runs this card's `reproduce.py` and the sibling's `reproduce.py`;
   both exit 0.
3. Commits and pushes from a human account, then ticks the MECHANICAL
   item on both cards and closes them with `goc done`.

## Artifacts

- reproduce.py
- pull-card-yml.patch

Surfaced by: general-purpose audit hunter (repo scripts and CI
workflows), 2026-09-28.

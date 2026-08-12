---
title: autonomous-pushes-do-not-trigger-ci-so-the-regression-suite-gates-nothing
summary: "Every commit on main since 2026-08-01 was pushed by the autonomous pull-card workflow using the default GITHUB_TOKEN, and GitHub does not start new workflow runs from GITHUB_TOKEN-authored pushes. So `ci.yml` — which AGENTS.md names as the gate for code correctness and card-frontmatter drift — has not run for 70 commits, and the regression suite has been red on main since 2026-08-04 with nobody told. The autonomous loop is committing to an unverified main by construction, not by accident."
status: open
stage: null
contribution: high
created: "2026-08-12T05:22:00Z"
closed_at: null
human_gate: session
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] PROCESS: the `## Decision required` mechanism question is answered by a
        human and recorded — which of the four options (or another) restores a
        gate on the autonomous path, and whether a green suite becomes a
        precondition for the bot's push or only an after-the-fact alarm
  - [ ] MECHANICAL: the chosen mechanism landed in `.github/workflows/`. This
        edit is human-only: AGENTS.md records that the autonomous bot's
        `GITHUB_TOKEN` cannot write files under `.github/workflows/`
  - [ ] EMPIRICAL: verified on a real bot push — after an autonomous
        `pull-card` run commits and pushes, the regression suite is observed to
        have executed against that exact commit, with the run URL recorded in
        `log.md`. A green run on a human push does NOT satisfy this; that is the
        path that already worked
  - [ ] EMPIRICAL: verified in the failing direction too — a deliberately red
        commit on a scratch branch (or a revert exercise) produces a visible
        failure signal through the chosen mechanism, so the gate is shown to
        discriminate rather than merely to exist
  - [ ] MECHANICAL: the 11-day blind window is reconciled — `uv run python -m
        unittest discover -s tests` and `uv run goc validate` are run against
        current `main` and the result recorded, so closing this card does not
        leave unknown breakage behind the newly-restored gate
  - [ ] MECHANICAL: AGENTS.md's CI paragraph states which pushes the suite
        actually gates. It currently reads as though every commit is gated,
        which is what let this run for 70 commits unnoticed
---

# CI has not run on main for 70 commits — the autonomous loop pushes past its own gate

## Location

- `.github/workflows/ci.yml:15-19` — the trigger block. No `paths` filter, so
  every push to `main` qualifies:

  ```yaml
  on:
    push:
      branches: [main]
    pull_request:
      branches: [main]
  ```

- `.github/workflows/ci.yml:56` — `Run regression tests`
  (`uv run python -m unittest discover -s tests`), the step AGENTS.md names as
  the gate for code correctness.
- `.github/workflows/pull-card.yml:48` — `actions/checkout@v6` with default
  `persist-credentials: true`, which leaves the default `GITHUB_TOKEN` in the
  git remote; `:116` — `GH_TOKEN: ${{ github.token }}`. The agent's `git push`
  therefore authenticates as `GITHUB_TOKEN`.

## What's broken

GitHub does not start new workflow runs from events triggered by the default
`GITHUB_TOKEN`. This repo already knows the rule — AGENTS.md cites it in the
release section, in the course of explaining why the tag re-dispatch works:

> `workflow_dispatch` is the documented exception to the rule that
> `GITHUB_TOKEN`-triggered events do not start new runs

`ci.yml` is triggered by `push`, not `workflow_dispatch`, and takes no
exception. So the rule applies to it in full: **no push made by the autonomous
workflow has ever started a CI run.**

The autonomous loop is the dominant author of `main`. Every commit since
2026-08-01 came from it, so CI last ran nearly two weeks ago, on the last
human push. AGENTS.md describes the arrangement as though it holds
unconditionally:

> the `Run regression tests` step (`uv run python -m unittest discover -s
> tests`) gates code correctness, and the validation step gates
> card-frontmatter drift.

It gates neither, on the path that produces almost all of the commits.

## Empirical evidence

`uv run python .game-of-cards/deck/autonomous-pushes-do-not-trigger-ci-so-the-regression-suite-gates-nothing/reproduce.py`:

```
ci.yml trigger block (no paths filter — every push to main qualifies):
  on:
    push:
      branches: [main]
    pull_request:
      branches: [main]

last commit CI is recorded to have run on : 0c6ac0a6 (2026-08-01, pushed with a human credential)
commits on main since it                  : 70
of those, pushed by the autonomous bot    : 70

most recent ci.yml run on main            : 2026-08-01T09:02:36Z (push, success) on 0c6ac0a6
current head is                           : 70 commits ahead of it

[DEFECT] ci.yml has not run on any of these commits: pushes made with the default GITHUB_TOKEN do not start new workflow runs, so the regression suite gates nothing on the autonomous path.
```

Every `ci.yml` run in the repo's history is a `push` event, and the ten most
recent all predate 2026-08-02. The `Pull Card` workflow, by contrast, has run
many times since — it is dispatched by `schedule` and `workflow_dispatch`,
both of which GitHub does start.

## Why it matters

The consequence is already sitting in the deck.
[regression-suite-red-on-main-over-the-unverified-tag-row](../regression-suite-red-on-main-over-the-unverified-tag-row/)
was filed 2026-08-06 for a suite that has been red since 2026-08-04, and its
body reasons about the breakage as loud:

> `.github/workflows/ci.yml` runs `uv run python -m unittest discover -s
> tests`, so every subsequent CI run on every Python version in the matrix
> fails until this is settled.

There have been no subsequent CI runs. The red test was found by a human or an
agent reading the deck, not by the gate — and it stayed open for eight days
because nothing was flashing. That card is the *instance*; this one is the
reason instances go unnoticed.

The failure mode is the worst-shaped kind: silent, and inverted from what the
docs say. A reader checking "is main healthy?" sees a green CI badge from the
last human push and a long clean run of autonomous commits underneath it. The
suite's 964 tests, the plugin-mirror byte-parity tripwire, the card-language
guard, the version-surface pins — none of them have run against `main` since
2026-08-01. Any one of them could already be red.

This also silently weakens the design decision that the mirror-parity guard
lives in a test rather than a `ci.yml` step (recorded in AGENTS.md, on the
grounds that the bot cannot edit workflow files). That reasoning assumed the
test suite runs; on the autonomous path it does not, so the guard moved from a
place the bot cannot break into a place nothing executes.

## Decision required

The fix is a workflow edit, which only a human can land — AGENTS.md records
that the autonomous bot's `GITHUB_TOKEN` cannot write under
`.github/workflows/`. The mechanism is a genuine pick, and the options differ
in more than plumbing:

- **A — Run the suite inside `pull-card.yml`, before the push.** Turns CI from
  an after-the-fact alarm into a precondition: the bot does not push a red
  tree. Cheapest to reason about and needs no new credential. Costs runtime in
  every pull-card run, and covers only the autonomous path (a human push still
  relies on `ci.yml`). Does not run the Python version matrix.
- **B — Add `workflow_run` chaining: `ci.yml` also triggers on completion of
  `Pull Card`.** `workflow_run` is dispatched by the Actions service, not by
  the pushing credential, so the `GITHUB_TOKEN` rule does not apply. Keeps the
  full matrix and one CI definition. Remains after-the-fact — a red commit is
  already on `main` when the alarm fires — and needs a rule for what happens
  next (revert? issue? nothing?).
- **C — Push with a PAT or GitHub App token instead of `GITHUB_TOKEN`.**
  Restores the plain `push` trigger for every path at once, so the docs become
  true as written. Introduces a long-lived credential with write access to
  `main`, which this repo has deliberately avoided elsewhere (the release flow
  is OIDC-only, and AGENTS.md notes that adding a `CLAWHUB_TOKEN` secret
  actively breaks releases). A GitHub App is the narrower variant.
- **D — Schedule `ci.yml` on a cron independent of pushes.** Trivial to land
  and independent of who pushed. Detects breakage within one interval rather
  than per-commit, and does not attribute a failure to a commit.

A and B are not exclusive: A gates the bot's own path, B keeps the matrix
honest. The second half of the question is policy rather than plumbing —
**should a green suite be a precondition for the bot's push (A), or an alarm
after it (B/D)?** The answer determines whether "the deck is the record" can
be trusted to mean the recorded work also built.

Whichever is picked, the blind window since 2026-08-01 needs reconciling
separately: current `main` has never been checked by the gate, so restoring
the gate may surface breakage that predates the fix.

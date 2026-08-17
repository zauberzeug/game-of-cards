---
title: failed-auto-commit-leaves-card-files-staged-in-the-shared-git-index
summary: "When `_git_auto_commit`'s `git commit` fails, the `git add` it ran first is never undone: the card's README.md and log.md stay staged in the shared git index, and the verb prints its success line and exits 0. A rejecting pre-commit hook is the routine trigger — this repo configures `goc validate` and the card-language guard to do exactly that. AGENTS.md § Parallel-Agent Commit Safety tells the next agent to read unexpected staged files as 'another agent is in its commit window', so goc manufactures a collision signal that never clears."
status: open
stage: null
contribution: high
created: "2026-08-13T05:06:47Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [ ] PROCESS: the `## Decision required` question below is answered and recorded via `Skill(decide-card)`, lowering the gate to `none`.
  - [ ] TDD: `reproduce.py` exits zero — after a rejected `git commit`, `git diff --cached --name-only` is empty.
  - [ ] TDD: a regression test asserts the pre-existing-stage case directly — a path the caller had already staged before the verb ran is left staged after a failed auto-commit, so the cleanup cannot be a blanket `git restore --staged` over the pathspec.
  - [ ] TDD: a regression test asserts the success path is unchanged — a normal auto-commit still lands one commit and leaves the index clean (`tests/test_git_auto_commit_pathspec.py` stays green).
  - [ ] MECHANICAL: the chosen remedy landed in `_git_auto_commit` (`goc/engine.py:4705-4819`) and its docstring's "Skipping is silent and non-fatal" paragraph states what happens to the index, not only to the disk mutation.
  - [ ] MECHANICAL: whichever of the exit-code / success-line options the decision picks is implemented consistently across all seven call sites (`engine.py:5853, 5763, 5959, 6216, 6238, 6253, 6582`), rather than in `_cmd_publish` alone.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass.
---

# A failed auto-commit leaves card files staged in the shared git index

## Location

- `goc/engine.py:4784` — `_git_auto_commit` stages the card's files:

  ```python
  subprocess.run(
      ["git", "add", "--", *paths],
      check=True, cwd=git_cwd, capture_output=True, text=True,
  )
  ```

- `goc/engine.py:4801-4817` — the commit, and the handler that swallows its
  failure:

  ```python
  subprocess.run(
      ["git", "commit", "-m", message, "--", *paths],
      check=True, cwd=git_cwd, capture_output=True, text=True,
  )
  return True
  except subprocess.CalledProcessError as e:
      print(f"  (auto-commit failed: {e})", file=sys.stderr)
      ...
      return False
  ```

  There is no `git restore --staged` / `git reset` on this path. The
  `git add` side effect survives the failure.

- Seven auto-committing call sites reach it: `goc status` (`engine.py:5853`),
  `goc publish` (`:5763`), `goc new --commit` (`:5959`), `goc wait` (`:6216`),
  `goc advance` (`:6238`), `goc unadvance` (`:6253`), `goc decide` (`:6582`).
  `auto_commit_enabled` (`engine.py:5045-5053`) defaults to **true** whenever
  the deck is git-tracked, so this is the default path, not an opt-in one.

## What's broken

`_git_auto_commit` makes two mutations: one to the working tree (done by the
caller, before it runs) and one to the **git index** (its own `git add`). Its
docstring reasons about only the first:

> Returns True if a commit landed; False if skipped (not a git repo,
> mid-merge/rebase/cherry-pick, no diff to commit, or git missing).
> **Skipping is silent and non-fatal — the state mutation already wrote to
> disk; an autocommit failure shouldn't roll that back.**

Not rolling back the *disk* write is right. But the function never considers
the *index* write it made itself, so a rejected commit returns with the
paths still staged — and the verb above it prints its success line and exits
`0`, because `_git_auto_commit`'s return value only decides whether to print
a `committed` line.

That collides head-on with this repo's own contract, AGENTS.md §
"Parallel-Agent Commit Safety":

> Treat Git's index as shared state: before staging, run
> `git diff --cached --name-only`. If it lists files you did not stage,
> another agent is in its commit window; wait with a short backoff or
> surface the collision instead of pushing through.

goc's failure path manufactures exactly that signal with no agent behind it.
An agent that obeys the protocol backs off from a commit window that will
never close; one that pushes through inherits two staged files it did not
stage — the case the same section's `git commit -- <path>...` pathspec rule
exists to contain ("The pathspec is the last guard against accidentally
bundling unrelated staged files").

The trigger is not exotic. `.pre-commit-config.yaml:16-18` says so in its own
comment:

> AGENTS.md § "Card authoring rules" requires English cards. goc's own
> auto-commit shells out to `git commit` without --no-verify, so this
> hook fires on `goc new --commit` too — the filing path, not just CI.

So the repo deliberately routes `goc validate` and the card-language guard
into the auto-commit's `git commit`. Any card those hooks reject — which is
their entire job — takes this path. Missing git identity, a failing
`commit.gpgsign`, and a contended `index.lock` reach it too.

## Empirical evidence

`uv run python .game-of-cards/deck/failed-auto-commit-leaves-card-files-staged-in-the-shared-git-index/reproduce.py`:

```
index before `goc publish` : (clean)
goc publish exit code      : 0
goc publish stdout         : 'staged-index-probe: published (draft flag cleared); now visible in the queue'
commits in history         : 1 (039a96f scaffold)
index after `goc publish`  : ['.game-of-cards/deck/staged-index-probe/README.md', '.game-of-cards/deck/staged-index-probe/log.md']

BUG: 2 path(s) left staged by the failed auto-commit: ['.game-of-cards/deck/staged-index-probe/README.md', '.game-of-cards/deck/staged-index-probe/log.md']
BUG: the verb exited 0 and printed its success line while nothing was committed
```

The probe plants a `pre-commit` hook that exits 1 — the shape pre-commit
installs — then publishes an authored card. Two paths enter a previously
clean index, nothing lands in history, and the verb reports success.

## Why it matters

The card that motivated this is `goc status <title> active` — the **soft
lock** every parallel-agent workflow depends on. When its auto-commit is
rejected, the claim exists only in the local working tree, the agent is told
`open → active` and exits 0, and the index is left dirty. So the failure is
simultaneously invisible on stdout, invisible to other agents (nothing was
committed), and *loudly misleading* to any agent that follows the documented
index check.

The autonomous loops make it self-sustaining: `pull-card.yml` runs unattended
with `--permission-mode bypassPermissions` and re-triggers itself up to
`MAX_ITERATIONS`, so nobody reads the stderr line that did report the
failure. Related but distinct:
[deck-auto-commit-sweeps-unrelated-staged-files-into-card-commits](../deck-auto-commit-sweeps-unrelated-staged-files-into-card-commits/)
(done) fixed goc *consuming* another agent's staged files by adding the
commit pathspec; this card is the same contract from the other side — goc
*producing* staged files that are nobody's. Neither
[auto-commit-guard-misses-paused-rebase-without-rebase-head-marker](../auto-commit-guard-misses-paused-rebase-without-rebase-head-marker/)
nor
[deck-auto-commit-prints-raw-git-output-before-the-verbs-own-report](../deck-auto-commit-prints-raw-git-output-before-the-verbs-own-report/)
touches the index-cleanup path: the first adds a pre-flight refusal, the
second only re-routed the diagnostic to stderr.

**Why this is a single-site defect, not a family.** The engine already has
the convention this call site is missing: the claim-push path aborts its own
half-finished git state on failure (`git rebase --abort`, `engine.py:5188`),
and `goc move`'s `git mv` falls back rather than stranding a side effect
(`engine.py:6519-6521`). `_git_auto_commit` is the outlier against a local
convention, and it is the one shared helper every auto-committing verb routes
through — so the fix is one function, not an architectural sweep. It is also
adjacent to but NOT a member of
[mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success](../mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success/):
that epic's eight children all accept *invalid input* where they should
refuse, whereas here the input is well-formed and an environmental step
fails. Deliberately left unwired (no `advances` edge), per the verdict
recorded on
[meta-fix-umbrella-cards-leave-sibling-family-advanced-by-edges-unwired](../meta-fix-umbrella-cards-leave-sibling-family-advanced-by-edges-unwired/)
that a single-site defect carrying zero edges is not rot; the epic's Scope
notes carry the reciprocal cross-reference.

## Decision required

Two independent questions, both with credible answers.

**1. What should the failure path do with the index?**

- **(a) Restore only what goc staged.** Snapshot
  `git diff --cached --name-only -- <paths>` *before* the `git add`, then on
  failure `git restore --staged` only the paths that were not already staged.
  Correct in the mixed case (a caller who had deliberately staged a card file
  keeps its staged state), at the cost of one extra git call on every
  auto-commit and a partially-staged-hunk edge case that no snapshot of file
  names can represent.
- **(b) Unconditional `git restore --staged -- <paths>` on failure.** One
  line, no pre-flight cost, but it resets a pre-existing staged entry to HEAD
  — destroying staging work goc did not do, which is the same class of harm
  AGENTS.md forbids (`git stash` / `git restore` are explicitly listed as
  operations that "can move or discard another agent's WIP").
- **(c) Do not stage at all.** Rejected on inspection, recorded so it is not
  re-litigated: a freshly scaffolded card is **untracked**, and
  `git commit -- <untracked-path>` fails with `pathspec ... did not match any
  file(s) known to git`. The `git add` is load-bearing for `goc new --commit`
  and `goc publish`, which are exactly the verbs that create files.

**2. Should the verb still report success and exit 0?**

Today the auto-commit result is advisory: `_git_auto_commit` returns `False`
for six benign reasons (no git repo, mid-rebase, nothing to commit, git
missing, all-drafts, no paths) as well as for a hard failure, and callers
treat them identically. Options: leave the exit code alone and only fix the
index (smallest change, keeps `goc` usable in non-git trees); distinguish
"skipped" from "failed" in the return type and print a visible warning on
stdout for the failure case; or make a hard commit failure non-zero. The
third changes the contract for every scripted caller — including
`pull-card.yml`, whose steps run under `set -e` — so it is the one that needs
the human's call rather than an agent's.

Note for whoever implements: `.github/workflows/` cannot be edited by the
autonomous bot's `GITHUB_TOKEN`, so if option 2c is chosen and any workflow
needs adjusting, that part is a human commit.

---
title: auto-commit-guard-misses-paused-rebase-without-rebase-head-marker
summary: "`_git_auto_commit` guards against committing mid-rebase by checking for the `REBASE_HEAD` file, but that sentinel is absent at a paused interactive-rebase stop (`break`/`edit`). Only `.git/rebase-merge/` (merge backend) and `.git/rebase-apply/` (apply backend) are reliably present throughout a rebase. So a GoC state-flip verb fired during a paused rebase injects an auto-commit into the rebase sequence — the exact corruption the guard exists to prevent."
status: active
stage: null
contribution: medium
created: "2026-06-19T05:19:40Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — with a paused interactive rebase in progress (`.git/rebase-merge/` present, no `REBASE_HEAD`), `_git_auto_commit` returns False, prints the skip message, and lands no commit
  - [ ] TDD: a regression test under tests/ pins the rebase-merge / rebase-apply sentinels (mirrors test_git_auto_commit_pathspec.py style)
  - [ ] MECHANICAL: `.git/rebase-merge` and `.git/rebase-apply` added to the in-progress sentinel set at engine.py:3898
  - [ ] `uv run python -m unittest discover -s tests` passes
  - [ ] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# Auto-commit guard misses a paused rebase (no `REBASE_HEAD` marker)

## Location

`goc/engine.py:3898` (inside `_git_auto_commit`).

## What's broken

`_git_auto_commit` documents its skip contract (engine.py:3874-3875):

> Returns True if a commit landed; False if skipped (not a git repo,
> **mid-merge/rebase/cherry-pick**, no diff to commit, or git missing).

It enforces the "mid-rebase" half with a single sentinel check:

```python
if any((git_dir / sf).exists() for sf in ("MERGE_HEAD", "REBASE_HEAD", "CHERRY_PICK_HEAD")):
    print("  (auto-commit skipped: merge/rebase/cherry-pick in progress)", file=sys.stderr)
    return False
```

`REBASE_HEAD` is the wrong sentinel for "a rebase is in progress." Git
writes `REBASE_HEAD` only transiently — it points at the commit currently
being applied or stopped-at, and it is **absent** at a `break` step and at
the gaps between commit replays. The marker that is reliably present for the
entire duration of a rebase is the per-backend state directory:
`.git/rebase-merge/` (the merge/interactive backend, today's default) or
`.git/rebase-apply/` (the apply/`am` backend). The guard checks neither.

So when a user has paused a rebase — e.g. an interactive rebase stopped at a
`break` or `edit` line — and an agent fires any auto-committing GoC verb
(`goc status active`, `advance`, `decide`, `wait`, `new --commit`, …),
`_git_auto_commit` does not see an in-progress rebase, proceeds, and runs
`git commit` in the middle of the rebase sequence. That is exactly the
corruption the guard exists to prevent.

## Empirical evidence

A `break`-step interactive rebase, inspecting `$GIT_DIR` (git 2.54.0):

```
=== break-step rebase ===
absent:  MERGE_HEAD
absent:  REBASE_HEAD
absent:  CHERRY_PICK_HEAD
PRESENT: rebase-merge
absent:  rebase-apply
```

`REBASE_HEAD` is gone; only `rebase-merge/` flags the in-progress rebase.
The current guard's sentinel set sees nothing and would let the commit
through. See `reproduce.py` for the end-to-end `_git_auto_commit` proof.

## Why it matters

`_git_auto_commit` is the shared commit path for every state-mutating GoC
verb (it is called from the `--commit` flows in `new`, `status`, `advance`,
`unadvance`, `decide`, `wait`). Agents are explicitly steered toward
preparing high-risk shared-`main` commits in worktrees and may have a rebase
paused on the deck tree. The guard already intends to no-op in that window
(the skip is silent and non-fatal by design); it simply uses a sentinel that
does not hold for the paused-rebase case. The reachability path is direct:
any `goc <verb> --commit` invoked while `.git/rebase-merge/` exists.

## Fix

Add the two rebase state directories to the sentinel tuple at
engine.py:3898 (`.exists()` already matches directories):

```python
if any(
    (git_dir / sf).exists()
    for sf in ("MERGE_HEAD", "REBASE_HEAD", "CHERRY_PICK_HEAD", "rebase-merge", "rebase-apply")
):
```

`REBASE_HEAD` is kept (harmless, and present during conflict resolution);
`rebase-merge` / `rebase-apply` close the paused-rebase gap.

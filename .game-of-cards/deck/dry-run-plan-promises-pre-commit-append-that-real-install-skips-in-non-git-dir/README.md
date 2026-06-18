---
title: dry-run-plan-promises-pre-commit-append-that-real-install-skips-in-non-git-dir
status: open
stage: null
contribution: medium
created: "2026-06-18T05:06:26Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
summary: |
  `_plan_writes` appends the `.pre-commit-config.yaml` write to the dry-run
  plan unconditionally, but the executor `_append_precommit_hook` skips it
  when `.git` is absent. So `goc install --dry-run` / `goc upgrade --dry-run`
  in a non-git directory promise a write (and inflate the "N writes planned"
  count) that the real run never performs.
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — the dry-run plan omits the .pre-commit-config.yaml append when the target has no .git, matching the executor
  - [ ] TDD: a regression test asserts dry-run/real parity for the pre-commit append in a non-git tmpdir (symmetric to the git-repo test added for goc-upgrade-omits-pre-commit-hook-append-promised-by-dry-run)
  - [ ] MECHANICAL: the "N writes planned" count drops by one in a non-git dir; no change to the git-repo dry-run plan
---

# dry-run-plan-promises-pre-commit-append-that-real-install-skips-in-non-git-dir

## Location

- `goc/install.py:863` — `_plan_writes` unconditionally appends
  `PlannedWrite("shared", "append", target / ".pre-commit-config.yaml", "guidance")`.
- `goc/install.py:1234-1238` — `_append_precommit_hook` is git-aware and
  returns early when `.git` is absent:
  `if not (target.parent / ".git").exists(): return`.

The plan is git-blind; the executor is git-aware. They disagree.

## What's broken

`_plan_writes` ends with:

```python
# goc/install.py:863
writes.append(PlannedWrite("shared", "append", target / ".pre-commit-config.yaml", "guidance"))
return writes
```

There is no `.git` guard, so the dry-run plan always lists the pre-commit
append. But the executor that actually performs it does guard:

```python
# goc/install.py:1234
def _append_precommit_hook(target: Path) -> None:
    """Append the `goc validate` hook to `.pre-commit-config.yaml` (creating it)."""
    if not (target.parent / ".git").exists():
        return
    ...
```

So in a non-git directory the dry-run preview claims a write the real run
silently skips.

## Empirical evidence

`reproduce.py` output on a clean checkout (in a non-git tmpdir):

```
  dry-run plan size: 19 writes
  plan lists .pre-commit-config.yaml append: True
  executor created .pre-commit-config.yaml: False

DEFECT REPRODUCED: dry-run plan promises a .pre-commit-config.yaml append the real run skips when .git is absent (plan/executor disagree).
```

Confirmed end-to-end at the CLI too: `goc install --dry-run` in a fresh
non-git directory prints `goc install (dry-run) — agents: claude — 19 writes
planned` and a `shared append .pre-commit-config.yaml` line, while the real
`goc install` in the same directory creates no `.pre-commit-config.yaml`.

## Why it matters

Both `install(dry_run=True)` and `upgrade(dry_run=True)` flow through
`_plan_writes` (upgrade via `_plan_upgrade_writes`, which keeps the `append`
action verbatim). The dry-run is documented as a truthful preview of what the
real run will do. Running GoC in a non-git directory is a documented, handled
case — it has its own closed card
[kickoff-and-install-handle-non-git-directories](../kickoff-and-install-handle-non-git-directories/),
which is exactly what made the *executor* git-aware while leaving the *plan*
git-blind. Anyone evaluating GoC by previewing `goc install --dry-run` before
`git init` sees a write that won't happen, and the "N writes planned" count is
off by one.

This is the inverse direction of the closed card
[goc-upgrade-omits-pre-commit-hook-append-promised-by-dry-run](../goc-upgrade-omits-pre-commit-hook-append-promised-by-dry-run/)
(commit bb01fcc), which fixed the *git-repo* case where the dry-run promised
the append and the real upgrade omitted it. That fix added the append to the
real upgrade in a git repo; it did not touch the non-git plan/executor
divergence.

## Fix

Gate the plan line on `.git` existence, mirroring the executor.
`_plan_writes` already receives `target`, so the check is available:

```python
# goc/install.py:863
if (target / ".git").exists():
    writes.append(PlannedWrite("shared", "append", target / ".pre-commit-config.yaml", "guidance"))
```

Add a regression test asserting dry-run/real parity in a non-git tmpdir —
the symmetric counterpart to the git-repo test already in `tests/test_install.py`.

Note: the executor checks `target.parent / ".git"` (it receives the
`.pre-commit-config.yaml` path), while the plan holds the repo dir as
`target` — so the plan-side check is `(target / ".git")`. Confirm the
worktree case (`.git` as a file) is covered by `.exists()` the same way the
executor handles it.

---
title: rebase-guard-test-uses-gnu-sed-syntax-and-fails-on-macos
summary: "test_git_auto_commit_rebase_guard seeds its paused interactive rebase with GIT_SEQUENCE_EDITOR='sed -i \"1a break\"' — GNU-only syntax that BSD/macOS sed rejects, so the rebase never pauses and the test fails at setup on every Mac while staying green on Linux CI. Fixed by editing the rebase todo with a portable Python sequence editor."
status: done
stage: null
contribution: low
created: "2026-07-14T05:00:45Z"
closed_at: "2026-07-14T05:08:55Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] TDD: tests/test_git_auto_commit_rebase_guard.py passes on macOS
    (BSD sed host) — setup produces a genuinely paused rebase
    (rebase-merge/ present, REBASE_HEAD absent) and the guard assertion
    still exercises the original defect.
  - [x] MECHANICAL: the sequence editor no longer shells out to sed at
    all — the todo edit is a Python helper script driven by
    sys.executable, portable across GNU/BSD userlands.
  - [x] PROCESS: full regression suite green on this macOS host;
    `uv run goc validate` passes.
worker: {who: Rodja Trappe, where: main}
---

# rebase-guard-test-uses-gnu-sed-syntax-and-fails-on-macos

## Why

`tests/test_git_auto_commit_rebase_guard.py` verifies that
`_git_auto_commit` refuses to commit during a paused interactive rebase.
To *create* that paused rebase it ran:

```python
env={**os.environ, "GIT_SEQUENCE_EDITOR": 'sed -i "1a break"'}
```

`sed -i "1a break"` is GNU sed syntax twice over: BSD/macOS sed requires
an (possibly empty) extension argument after `-i`, and its `a` command
needs a backslash-newline form. On macOS the editor exits non-zero, git
aborts the rebase, `.git/rebase-merge/` never exists, and the test dies
in its own setup assertion:

```
AssertionError: False is not true : setup failed: expected a paused rebase (rebase-merge/ present)
```

Linux CI (GNU sed) stays green, so the failure only surfaces on
developer Macs — where it reads as a scary local regression during
unrelated work (it surfaced while verifying the codex hooks fix on
[codex-plugin-upgrade-deletes-hook-scripts-under-running-sessions](../codex-plugin-upgrade-deletes-hook-scripts-under-running-sessions/)).

## Fix

Replace the sed one-liner with a sequence editor that has no userland
variance: a tiny Python helper written into the test's temp dir which
inserts `break` after the first todo line, invoked via
`f'"{sys.executable}" "{editor}"'`. Verified on macOS (git 2.50.0,
BSD sed): setup now yields the paused rebase and the test passes; the
guard logic under test is unchanged.

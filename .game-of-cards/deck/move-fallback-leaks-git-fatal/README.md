---
title: move-fallback-leaks-git-fatal
summary: "`goc move` falls back from `git mv` to `shutil.move` outside git repositories, but the failed `git mv` subprocess writes `fatal: not a git repository` to stderr before the successful move. The command exits zero while still showing a scary failure."
status: done
stage: null
contribution: medium
created: 2026-05-04
closed_at: 2026-05-05
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] `uv run python deck/move-fallback-leaks-git-fatal/reproduce.py` exits zero
  - [x] `goc move` in a non-git directory exits zero with no git fatal text on stderr
  - [x] The fallback still renames the card and rewrites relation fields
  - [x] Regression coverage asserts stderr is clean for the non-git fallback path
---

# move-fallback-leaks-git-fatal

## Location

- `goc/engine.py:1761`
- `tests/test_install.py:421`

## What's broken

`move()` attempts `git mv` and falls back to `shutil.move`:

```python
try:
    subprocess.run(["git", "mv", str(src), str(dst)], cwd=REPO_ROOT, check=True)
except (subprocess.CalledProcessError, FileNotFoundError):
    shutil.move(str(src), str(dst))
```

The subprocess does not capture stderr. In a non-git repo, `git mv`
prints `fatal: not a git repository...` even though the fallback succeeds
and the command exits zero.

The existing move test uses a temp directory without git, so it exercises
the fallback path, but it does not assert stderr is clean.

## Empirical evidence

Current output from `uv run python deck/move-fallback-leaks-git-fatal/reproduce.py`:

```text
create_exit=0
move_exit=0
move_stdout=source-card → renamed-card
move_stderr=fatal: not a git repository (or any of the parent directories): .git
renamed_exists=True
defect present: successful non-git move leaks git fatal stderr
```

## Why it matters

GoC works as plain markdown files and should not require git for basic
deck operations. A successful non-git move should not print a fatal git
message; users and automation read stderr as a failure signal.

## Fix

Capture stdout/stderr for the attempted `git mv`, or check whether the
target is inside a git worktree before trying it. Only surface git errors
when git was expected to handle the move and the fallback also cannot
complete safely.

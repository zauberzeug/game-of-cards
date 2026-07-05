---
title: claiming-a-card-crashes-when-git-is-not-on-path
summary: "`goc status <title> active` aborts with a raw FileNotFoundError traceback when the `git` binary is not on PATH: `_auto_populate_worker` runs `git config user.name` / `git rev-parse --abbrev-ref HEAD` with no FileNotFoundError/TimeoutExpired handling, while every other git call site in the engine tolerates a missing binary. Fix: match the engine's own convention and treat a missing git like a nonzero exit."
status: done
stage: null
contribution: medium
created: "2026-07-05T01:33:09Z"
closed_at: "2026-07-05T01:43:36Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (claiming with git absent from PATH no longer raises FileNotFoundError)
  - [x] TDD: regression test asserts `_auto_populate_worker` leaves the card text unchanged when the git binary is missing (no worker stamped, no exception)
  - [x] MECHANICAL: both subprocess calls in `_auto_populate_worker` catch `(FileNotFoundError, subprocess.TimeoutExpired)` and fall back to the same "git said no" branch as a nonzero exit
  - [x] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` pass
worker: {who: "claude[bot]", where: main}
---

# Claiming a card crashes with a raw traceback when `git` is not on PATH

## Location

`goc/engine.py:5096` and `goc/engine.py:5102` (`_auto_populate_worker`).

## What's broken

The claim verb (`goc status <title> active`) auto-populates the `worker`
field by shelling out to git — with no protection against the binary being
absent:

```python
r = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, timeout=5)
who = r.stdout.strip() if r.returncode == 0 else ""
```

```python
r = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, timeout=5)
where = r.stdout.strip() if r.returncode == 0 else None
```

`subprocess.run` raises `FileNotFoundError` when the executable does not
exist, regardless of `capture_output` — the `returncode` fallbacks only
cover git *failing*, not git *missing*. In a git-less environment (minimal
container, PATH-stripped CI runner) the claim aborts with an unhandled
traceback ending `FileNotFoundError: [Errno 2] No such file or directory:
'git'`.

This is an outlier against the engine's own convention. Every other git
call site explicitly tolerates a missing binary: `_detect_worktree_common_root`
(`engine.py:58`), `_git_auto_commit` (`engine.py:4404`), `_deck_is_git_tracked`
(`engine.py:4461`), `_move_iter_tracked_text_files` (`engine.py:5774`), and
`_cmd_move` (`engine.py:5864`) all catch `FileNotFoundError`. The
git-dependent claim-push and closure-on-integration paths are additionally
guarded by `_deck_is_git_tracked()` (which returns False git-less), so
`_auto_populate_worker` is the one reachable crash site.

## Empirical evidence

`uv run python .game-of-cards/deck/claiming-a-card-crashes-when-git-is-not-on-path/reproduce.py`:

```
PATH stripped of git; calling _auto_populate_worker ...
DEFECT: FileNotFoundError raised: [Errno 2] No such file or directory: 'git'
```

## Why it matters

`goc new` works git-less, and the engine's data model does not require git
(auto-commit and claim-push silently no-op when the deck is not
git-tracked). So a user in a git-less environment can create cards but
cannot claim them — the crash lands before the status flip is written
(`engine.py:5223`), so the claim is lost, not half-applied. The reachability
path is any `goc status <title> active` invocation without `--worker`
overrides on a host without git.

## Fix

Wrap each of the two subprocess calls in
`try: ... except (FileNotFoundError, subprocess.TimeoutExpired):` and fall
back to the same value the existing nonzero-`returncode` branch produces
(`who = ""` / `where = None`). The downstream empty-`who` guard already
handles the "no detectable worker" case by leaving the card untouched.

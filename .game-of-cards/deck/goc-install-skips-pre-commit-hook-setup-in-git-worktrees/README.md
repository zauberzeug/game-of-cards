---
title: goc-install-skips-pre-commit-hook-setup-in-git-worktrees
summary: "`goc install` skips the `.pre-commit-config.yaml` setup whenever it runs inside a git worktree. The guard at `goc/install.py:944` tests `(target.parent / \".git\").is_dir()`, but in a git worktree `.git` is a *file* (containing `gitdir: …`), not a directory — so `is_dir()` returns False and the function returns early. The worktree is unambiguously a git checkout (an `exists()` test would correctly accept it)."
status: active
stage: null
contribution: medium
created: "2026-05-30T01:20:53Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero (after the fix, `_append_precommit_hook` writes `.pre-commit-config.yaml` when invoked inside a git worktree).
  - [ ] MECHANICAL: the guard at `goc/install.py:944` no longer rejects worktrees (use `exists()` rather than `is_dir()`, or detect the `gitdir:` file form explicitly).
  - [ ] TDD: a regression test in `tests/` covers the worktree shape (e.g. set up a temp worktree, call `_append_precommit_hook`, assert the file lands).
  - [ ] MECHANICAL: `uv run goc validate` clean; plugin-asset sync `--check` green.
worker: {who: "claude[bot]", where: main}
---

# goc install skips pre-commit hook setup in git worktrees

## Location

- `goc/install.py:944` — `if not (target.parent / ".git").is_dir(): return`
- Caller: `goc/install.py:1176` — `_append_precommit_hook(target / ".pre-commit-config.yaml")` (invoked from the `install` flow only; `upgrade` does not re-run this step).

## What's broken

`_append_precommit_hook` is meant to skip the pre-commit hook install
when the target directory is not a git checkout. The intent is correct;
the test is wrong. From `goc/install.py:941-945`:

```python
def _append_precommit_hook(target: Path) -> None:
    """Append the `goc validate` hook to `.pre-commit-config.yaml` (creating it)."""

    if not (target.parent / ".git").is_dir():
        return
```

In a *git worktree* (created via `git worktree add …`), `<worktree>/.git`
is a **file** whose contents look like `gitdir: /path/to/main/.git/worktrees/<branch>`
— not a directory. `Path.is_dir()` returns False for a regular file, so
the guard fires and the function returns without writing
`.pre-commit-config.yaml`, even though the worktree is unambiguously a
git checkout.

The result: a user who runs `goc install` from inside a worktree gets a
clean `goc <version> installed …` success message, but the
`.pre-commit-config.yaml` step silently no-ops. They have to discover
the gap themselves — there is no diagnostic.

## Empirical evidence

`reproduce.py` (run via `uv run python deck/<title>/reproduce.py`)
constructs a fresh main repo + worktree, invokes
`_append_precommit_hook` against the worktree's
`.pre-commit-config.yaml`, and reports the outcome:

```
worktree .git is_dir() : False
worktree .git is_file(): True
worktree .git exists() : True
FAIL: worktree/.pre-commit-config.yaml NOT written — _append_precommit_hook returned early because (.git).is_dir() is False in a worktree
exit=1
```

The three probes at the top demonstrate the root cause: `.git` exists,
is a file, and is not a directory. The same probes run against the main
repo would show `is_dir() == True` and the function would proceed.

## Why it matters

`goc install` is the only call site, and it runs once per repo
checkout. The reachability path is:

- User creates a git worktree (`git worktree add ../foo -b feature/foo`)
  of a non-GoC project — this is a common workflow for collaborators
  who want to keep main pristine while developing on a branch tree.
- User runs `goc install` inside the worktree.
- The `install()` function (`goc/install.py:1099-1188`) writes
  `.game-of-cards/`, agent harness, briefing block, etc. — all of
  which succeed — and then calls `_append_precommit_hook`, which
  silently returns. The user is left without the `goc-validate`
  pre-commit guard.

This bug is also load-bearing for any flow that asks "is this a git
checkout?" via the same shape — the antipattern is reusable and the
fix is uniform.

## Fix

One-line change at `goc/install.py:944`:

```diff
-    if not (target.parent / ".git").is_dir():
+    if not (target.parent / ".git").exists():
         return
```

`Path.exists()` returns True for both the directory form (regular
checkout) and the file form (worktree). It correctly rejects
non-git-checkout directories (where `.git` doesn't exist at all). The
remaining body of `_append_precommit_hook` is unaffected because it
only writes the `.pre-commit-config.yaml` (sibling of the `.git`
file/dir), not anything inside `.git/`.

If finer detection is wanted (e.g. tell apart "real worktree" from
"random file named .git"), parse the file's first line — but
`exists()` matches the original intent: "skip the hook unless this is
a git checkout."

## Sibling sweep

`grep -rn '"\\.git"' goc/` returns this one site as the only
`.is_dir()` test against `.git` inside the goc package, so the fix
is one-shot — no companion sites to patch in lockstep.

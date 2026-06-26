---
title: goc-move-runs-git-operations-in-the-wrong-tree-under-shared-deck-worktree-mode
status: open
stage: null
contribution: medium
created: "2026-06-26T02:31:35Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] `_cmd_move`'s `git mv` (`engine.py:5483`) and `_move_iter_tracked_text_files`'s `git ls-files` (`engine.py:5380`) run with `cwd=str(DECK_ROOT)`, matching `_git_auto_commit` / `_git_claim_push_with_retry` / `_enforce_closure_on_integration_or_exit`
  - [ ] under shared-deck worktree mode, `goc move <old> <new>` produces a clean `R` rename in the deck tree (not `D old` + `?? new`)
  - [ ] the moved card's own `title:` field is rewritten (not left stale, which would fail `goc validate`)
  - [ ] regression test covering the shared-deck-worktree move path (or a unit test asserting the move helpers resolve their git cwd to `DECK_ROOT`)
  - [ ] `reproduce.py` exits non-zero before the fix, zero after
  - [ ] full suite + `goc validate` clean
---

# goc-move-runs-git-operations-in-the-wrong-tree-under-shared-deck-worktree-mode

`goc move` is the only deck-mutating verb that still runs its git operations
in `REPO_ROOT` instead of `DECK_ROOT`. Every other git op that touches deck
files deliberately uses `git_cwd = str(DECK_ROOT)`:

- `_git_auto_commit` — `engine.py:4159`
- `_enforce_closure_on_integration_or_exit` — `engine.py:4301`
- `_git_claim_push_with_retry` — `engine.py:4365`

But the move path uses `REPO_ROOT`:

```python
# _move_iter_tracked_text_files, engine.py:5380
cwd=str(REPO_ROOT), capture_output=True, check=True, timeout=30,

# _cmd_move, engine.py:5483
subprocess.run(["git", "mv", str(src), str(dst)], cwd=REPO_ROOT, check=True, capture_output=True)
```

## Why it matters

In shared-worktree-deck mode (`GOC_WORKTREE_DECK=shared` or
`workflow.worktree_deck: shared`), `DECK_ROOT` is the **primary** working
tree where the deck's card files are tracked, and `REPO_ROOT` is the
**linked** worktree the user is running `goc` from — different directories.
Running `goc move <old> <new>` from the linked worktree then:

1. `git mv` is invoked with `cwd=REPO_ROOT` against absolute paths under
   `DECK_ROOT` (outside that worktree) → it errors, the error is **swallowed**
   by the `except (CalledProcessError, FileNotFoundError)` at
   `engine.py:5484`, and the code falls through to `shutil.move`. The deck
   tree is left half-staged (`D old/README.md`, `?? new/`) — a broken rename
   with no `R` entry.
2. `_move_rewrite_tracked_files` → `_move_iter_tracked_text_files` calls
   `git ls-files` in `REPO_ROOT`, which lists none of the deck files, so the
   moved card's own frontmatter is never rewritten: `new/README.md` still
   contains `title: <old>`, which fails `goc validate` (title ≠ dir name).
   Cross-references in other cards are likewise missed.

## Reachability path

Set up a primary repo with `.game-of-cards/deck/`, add a linked git worktree,
enable shared-deck mode, then from the linked worktree run
`goc move <old> <new>`. (Single-tree mode is unaffected because there
`DECK_ROOT == REPO_ROOT`.)

## Distinct from existing cards

- `goc-move-leaves-cross-reference-rewrites-uncommitted` — the *single-tree*
  case where rewrites succeed but aren't committed; orthogonal (here the
  rewrites don't even happen and the rename itself isn't tracked).
- `openclaw-resolve-deck-dir-ignores-git-worktree-shared-deck-resolution` —
  the OpenClaw TS hook's deck-dir resolution, a different code path.

## Fix shape

Single-site mirror of the rest of the file: resolve `git mv` and `git
ls-files` in the move path against `str(DECK_ROOT)` (the `git_cwd` the
auto-commit / claim-push helpers already compute), and build the rewrite
candidate paths relative to that tree rather than `REPO_ROOT`.

> Surfaced by a pull-card audit hunter (empty ready queue); verified by
> reading the cited lines but not yet reproduced end-to-end with a live
> worktree — a fresh-context run should author `reproduce.py` against an
> actual shared-deck worktree before closing.

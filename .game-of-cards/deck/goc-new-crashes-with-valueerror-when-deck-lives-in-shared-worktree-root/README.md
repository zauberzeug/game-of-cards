---
title: goc-new-crashes-with-valueerror-when-deck-lives-in-shared-worktree-root
summary: "`goc new`'s final success/next-step prints call `card_dir.relative_to(REPO_ROOT)`. In shared-worktree-deck mode DECK_ROOT (primary tree) != REPO_ROOT (linked worktree), so card_dir lives outside REPO_ROOT and the call raises ValueError — after the card is already written to disk. The command half-succeeds and crashes with an uncaught traceback instead of printing the next-step hint."
status: done
stage: null
contribution: medium
created: "2026-06-24T07:37:14Z"
closed_at: "2026-06-24T07:43:04Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: a regression test constructs a card_dir outside REPO_ROOT (as in shared-worktree mode) and asserts the success-message path-display does not raise ValueError
  - [x] TDD: reproduce.py exits zero after the fix (defect no longer fires)
  - [x] MECHANICAL: engine.py:4917-4918 no longer use relative_to(REPO_ROOT) for card_dir; they use a crash-proof display (relative_to(DECK_ROOT) or _display_path), matching the established pattern at engine.py:4291
  - [x] MECHANICAL: non-worktree output is unchanged (still prints `.game-of-cards/deck/<title>/`)
  - [x] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# `goc new` crashes with ValueError when the deck lives in a shared worktree root

## Location

`goc/engine.py:4917-4918` — the success-message block at the end of `_cmd_new`:

```python
    print(f"created {card_dir.relative_to(REPO_ROOT)}/")
    print(f"Next: edit {card_dir.relative_to(REPO_ROOT)}/README.md to fill the body and DoD; then ask your agent to implement the card.")
```

## What's broken

`card_dir = DECK_DIR / title` (`engine.py:4881`), and `DECK_DIR` is rooted at
`DECK_ROOT` (`engine.py:122-123`):

```python
DECK_ROOT = _resolve_deck_root(REPO_ROOT)
DECK_DIR = _resolve_deck_dir(DECK_ROOT)
```

In **shared-worktree-deck mode** — `GOC_WORKTREE_DECK=shared` or
`workflow.worktree_deck: shared` in the common root's `config.yaml` —
`_resolve_deck_root` returns the *primary* working tree, not the current
linked worktree (`engine.py:80-94`):

```python
    if os.environ.get("GOC_WORKTREE_DECK", "").lower() == "shared":
        return common_root
    ...
            if (cfg.get("workflow") or {}).get("worktree_deck") == "shared":
                return common_root
```

So `DECK_ROOT` (hence `DECK_DIR` and `card_dir`) lives **outside**
`REPO_ROOT = Path.cwd()` (`engine.py:36`). `Path.relative_to(REPO_ROOT)`
then raises `ValueError: '<...>/.game-of-cards/deck/<title>' is not in the
subpath of '<cwd>'`.

The rest of the function already knows deck files live under `DECK_ROOT`,
not `REPO_ROOT` — the git operations explicitly switch to `DECK_ROOT`
(`engine.py:4033-4036`, `4061`, `4291`):

```python
    # Deck files may live in the shared primary working tree (DECK_ROOT),
    # not the current worktree (REPO_ROOT). Git operations on deck files
    # must use DECK_ROOT so relative paths and staging work correctly.
    git_cwd = str(DECK_ROOT)
```

Only the final two `print` statements were left on `REPO_ROOT`, so they
crash in exactly the mode the rest of the function was written to support.

## Empirical evidence

`uv run python .game-of-cards/deck/goc-new-crashes-with-valueerror-when-deck-lives-in-shared-worktree-root/reproduce.py`:

```
REPO_ROOT (cwd / linked worktree): /tmp/worktrees/feature-branch
DECK_ROOT (shared primary tree):   /tmp/primary
card_dir:                          /tmp/primary/.game-of-cards/deck/my-new-card

relative_to(REPO_ROOT) raised ValueError:
    '/tmp/primary/.game-of-cards/deck/my-new-card' is not in the subpath of '/tmp/worktrees/feature-branch'

relative_to(DECK_ROOT) -> .game-of-cards/deck/my-new-card   [crash-proof, matches engine.py:4291]

DEFECT CONFIRMED: `goc new` would crash after writing the card to disk.
```

## Why it matters

Reachability: shared-worktree-deck mode is a shipped, documented feature
(`_resolve_deck_root`, the `GOC_WORKTREE_DECK` env var, and the
`workflow.worktree_deck: shared` config key). Any agent running
`goc new` from a linked worktree in that mode hits this. The card
directory and `README.md` / `log.md` are written first (`engine.py:4893`,
`4911-4912`), then the print throws — so the user gets a half-completed
command: the card exists on disk, but the command exits non-zero with a
Python traceback and never prints the "Next: edit ..." guidance. Worse,
if `--commit` was requested, the commit step (`engine.py:4923`) is never
reached because the exception fires first, leaving the new card uncommitted.

## Fix

Switch both prints from `relative_to(REPO_ROOT)` to `relative_to(DECK_ROOT)`.
`card_dir` is always under `DECK_DIR ⊆ DECK_ROOT`, so this can never raise,
and it matches the established precedent at `engine.py:4291`. In the
non-worktree case `DECK_ROOT == REPO_ROOT`, so the printed path is
byte-identical to today (`.game-of-cards/deck/<title>/`).

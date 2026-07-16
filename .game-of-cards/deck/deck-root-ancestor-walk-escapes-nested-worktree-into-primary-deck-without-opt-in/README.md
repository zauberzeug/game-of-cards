---
title: deck-root-ancestor-walk-escapes-nested-worktree-into-primary-deck-without-opt-in
summary: "The deck-root fallback ancestor walk added by `fix: resolve new cards to existing deck root` runs unconditionally after the opt-in shared-worktree gate declines, so a linked worktree nested inside the primary tree (`git worktree add wt/feature`) silently resolves — and writes — to the primary tree's deck with no `GOC_WORKTREE_DECK`/config opt-in. The same walk also crosses into an enclosing unrelated repository. Fix: let the walk climb plain ancestor directories (the workspace-deck case its own test pins) but stop before entering a different git working tree."
status: done
stage: null
contribution: medium
created: "2026-07-16T01:02:01Z"
closed_at: "2026-07-16T01:11:44Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (goc new from a deck-less nested worktree without shared-mode opt-in refuses instead of writing into the primary tree's deck)
  - [x] TDD: regression test covers the boundary rule — nested worktree refuses; repo nested in a deck-owning repo refuses; subdir-of-repo and plain-workspace resolution (the behavior 3e17e3b3 added) still work
  - [x] MECHANICAL: `_resolve_deck_root`'s docstring states the walk stops before entering a different git working tree and that cross-tree sharing stays opt-in
  - [x] EMPIRICAL: full regression suite passes (`uv run python -m unittest discover -s tests`), including tests/test_new_resolves_existing_deck_root.py
worker: {who: "claude[bot]", where: main}
---

# Deck-root ancestor walk escapes a nested worktree into the primary deck without opt-in

## Location

`goc/engine.py:99-102` (`_resolve_deck_root`), introduced 2026-07-15 by
commit `3e17e3b3` "fix: resolve new cards to existing deck root":

```python
    for candidate in (cwd, *cwd.parents):
        if (candidate / ".game-of-cards").is_dir():
            return candidate
    return cwd
```

## What's broken

The walk runs *after* the shared-worktree gate at `engine.py:85-97`
has already declined (no `GOC_WORKTREE_DECK=shared`, no
`workflow.worktree_deck: shared` in the common root's config). It is
bounded only by the filesystem root, so it crosses git working-tree
boundaries:

- A linked worktree created **inside** the primary tree
  (`git worktree add wt/feature` — a common layout) that has no deck
  of its own walks up past its own tree root, hits the primary tree's
  `.game-of-cards/`, and returns the primary root. Every verb —
  including `goc new` — then silently operates on the **primary
  tree's deck**, even though shared-deck mode was never opted into.
- A repository nested inside another repository that has a deck
  inherited the *outer project's* deck the same way.

One nesting shape is deliberate, not broken: commit 3e17e3b3's own
test `test_new_from_nested_repo_uses_ancestor_deck` pins that a
deck-less nested repo inherits a deck from an enclosing **plain
workspace** directory (a workspace holding several repos owns one
deck above them). The boundary rule must preserve that while
refusing foreign *working trees*.

The contract this violates is pinned by the closed spike
[spike-worktree-auto-resolves-deck-from-main-repo](../spike-worktree-auto-resolves-deck-from-main-repo/),
whose DoD states:

> Behavior is opt-in via `.game-of-cards/config.yaml` (or env var) —
> some users may want a per-worktree deck (parallel experiments).

The walk overrides that opt-in default based purely on directory
nesting — and inconsistently: an identical deck-less worktree placed
as a **sibling** of the primary tree (`git worktree add ../feature`)
gets the intended `ERROR: no Game of Cards deck found … Run 'goc
install'` refusal, while the nested one silently writes cross-tree.

## Empirical evidence

`reproduce.py` builds a primary repo with a deck, adds a deck-less
nested worktree at `wt/feature`, and runs `goc new` from it with
shared mode NOT opted in. Observed on the defective code:

```
goc new exit code: 0
card dir exists under PRIMARY tree: True
card dir exists under worktree:     False
DEFECT: nested worktree silently wrote into the primary tree's deck
```

## Why it matters

Reachability: any consumer who keeps worktrees inside the repo
(`wt/`, `.worktrees/`, `worktrees/` layouts are all common) and runs
any goc verb from one. The card lands in a working tree the user is
not committing from, so it also evades the worktree's commit flow —
the user's own checkout shows nothing to commit while the primary
tree accumulates unexplained dirty state (surprising under the
parallel-agent commit-safety rules this project documents).

## Fix (implemented)

`goc/engine.py` `_resolve_deck_root`: the walk tracks when it has
passed the current tree's own root (the first candidate carrying a
`.git` entry — dir for a primary tree, file for a linked worktree).
At each candidate it checks `.game-of-cards/` first (so a repo root
holding both `.git` and a deck still resolves), and breaks when a
candidate *above* the own-tree root carries `.git` — that candidate
is a different working tree, and inheriting its deck would share
state across trees without the `worktree_deck=shared` opt-in.
Plain-directory ancestors (the pinned workspace case) and non-git
trees keep the walk-to-root behavior. Regression tests:
`test_new_from_nested_worktree_refuses_without_shared_opt_in` and
`test_new_from_repo_nested_in_deck_owning_repo_refuses` in
`tests/test_new_resolves_existing_deck_root.py`. Mirror trees
regenerated via `scripts/sync_plugin_assets.py`.

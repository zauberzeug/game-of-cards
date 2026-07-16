---
title: deck-root-ancestor-walk-escapes-nested-worktree-into-primary-deck-without-opt-in
summary: "The deck-root fallback ancestor walk added by `fix: resolve new cards to existing deck root` runs unconditionally after the opt-in shared-worktree gate declines, so a linked worktree nested inside the primary tree (`git worktree add wt/feature`) silently resolves — and writes — to the primary tree's deck with no `GOC_WORKTREE_DECK`/config opt-in. The same walk also crosses into an enclosing unrelated repository. Fix: stop the walk at the current working tree's boundary (first ancestor carrying a `.git` entry)."
status: active
stage: null
contribution: medium
created: "2026-07-16T01:02:01Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero (goc new from a deck-less nested worktree without shared-mode opt-in refuses instead of writing into the primary tree's deck)
  - [ ] TDD: regression test covers the boundary rule — nested worktree stops at its own tree root; subdir-of-repo resolution (the behavior 3e17e3b3 added) still works; non-git ancestor walk still works
  - [ ] MECHANICAL: `_resolve_deck_root`'s docstring states the walk stops at the first ancestor containing a `.git` entry
  - [ ] EMPIRICAL: full regression suite passes (`uv run python -m unittest discover -s tests`), including tests/test_new_resolves_existing_deck_root.py
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
  inherits the *outer project's* deck the same way.

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

## Fix

Bound the walk at the current working tree's boundary: at each
candidate, check `.game-of-cards/` first (so a repo root that has
both `.git` and a deck still resolves), then stop if the candidate
contains a `.git` entry (`(candidate / ".git").exists()` — covers
both the primary tree's `.git/` dir and a linked worktree's `.git`
file). Non-git directory trees keep today's walk-to-root behavior;
subdir-of-repo resolution (the case 3e17e3b3 fixed) is unaffected
because the repo root carrying `.game-of-cards/` is checked before
its `.git` stops the walk. Mirror trees regenerate via
`scripts/sync_plugin_assets.py` on commit.

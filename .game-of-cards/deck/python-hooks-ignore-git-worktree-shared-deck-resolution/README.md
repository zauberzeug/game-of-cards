---
title: python-hooks-ignore-git-worktree-shared-deck-resolution
summary: "UNVERIFIED. The Python SessionStart and Stop hooks find the deck with a copy of the engine's upward walk but not its worktree_deck: shared redirect, so in a linked worktree they read the worktree's own checkout instead of the shared deck goc uses. The session-start reminder then stays silent about active cards goc lists, and the Stop hook reads the wrong config — the Python sibling of the open OpenClaw resolveDeckDir card."
status: open
stage: null
contribution: medium
created: "2026-10-05T01:32:49Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, unverified]
definition_of_done: |
  - [ ] TDD: a reproduce.py builds a primary repo with `workflow.worktree_deck: shared`, adds a linked worktree, claims a card from it with `goc`, and asserts `deck_session_start.py` run with `cwd` = the linked worktree names that card — or the run disproves the hypothesis and the card flips to `disproved`
  - [ ] TDD: `tests/test_project_root_from_subdirectory.py` gains a shared-deck worktree layout, so the hook-versus-engine agreement test covers the redirect and not only the walk
  - [ ] MECHANICAL: both Python hooks resolve the shared deck the way `goc.engine._resolve_deck_root` does (env var and common-root config), and their docstrings stop calling the walk alone a mirror of `_resolve_deck_root`; mirrors re-synced; drop the `unverified` tag once reproduce.py lands
  - [ ] PROCESS: connected to `session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting` and cross-linked with `openclaw-resolve-deck-dir-ignores-git-worktree-shared-deck-resolution`
---

# Python hooks ignore git-worktree shared-deck resolution

> **UNVERIFIED.** Surfaced by the general-purpose hunter of the 2026-10-05
> audit-deck pass. The filing agent re-read the citations and reproduced the
> session-start half by hand (below). No `reproduce.py` was written this
> round; the falsification recipe is below.

## Location

- `goc/templates/hooks/deck_session_start.py:274-292`: `_find_project_dir`,
  the upward walk. Its docstring: "This is a mirror of the walk in
  `goc.engine._resolve_deck_root` — hooks import nothing from the package —
  pinned to it by tests/test_project_root_from_subdirectory.py." The hook calls
  it at `:310`.
- `goc/templates/hooks/pattern_generalization_check.py:92`: the same walk;
  `:121` reads `.game-of-cards/config.yaml` under whatever it returns; called at
  `:239`.
- `goc/engine.py:106-121`: `_resolve_project_roots`, which consults
  `_shared_worktree_deck_root(cwd)` (`:72-89`) before the walk and, in a linked
  worktree with `worktree_deck: shared` (config in the common root, or
  `GOC_WORKTREE_DECK=shared`), returns the primary tree as the deck root.
  Neither hook has an equivalent; `grep worktree goc/templates/hooks/*.py`
  finds nothing.
- `goc/engine.py:142-143`: "The runtime hooks carry a mirror of the walk
  (`_find_project_dir`), pinned to this function by
  tests/test_project_root_from_subdirectory.py." The pin's fixture
  (`tests/test_project_root_from_subdirectory.py:176-194`, `layouts()`) has no
  worktree layout, so the redirect is outside what it compares.
- The promise: `goc/templates/skills/kickoff/reference.md:55-58` — set
  `worktree_deck: shared` "to make all linked worktrees share the deck in the
  primary working tree."

## Hypothesis

`goc-finds-the-deck-from-a-subdirectory-but-attests-validates-and-installs-there`
(closed) gave the hooks a copy of the engine's walk, not of the redirect that
precedes it. In a linked worktree of a repo that tracks `.game-of-cards/`, the
walk stops at the worktree's own checkout. Its deck is a copy at that branch's
commit, while `goc` reads and writes the primary tree's deck.

Run by hand: primary repo after `goc install --agents claude`, with the
template's `worktree_deck: shared` line uncommented and committed, then
`git worktree add ../linked`. From `linked/`, `goc new` and `goc status … active`:

```
created .game-of-cards/deck/claimed-card-from-worktree/      # in primary/, as configured
goc --status active (from linked/)          -> lists claimed-card-from-worktree
deck_session_start.py, cwd=linked/          -> (no output), exit 0
deck_session_start.py, cwd=primary/         -> [GoC] Active card(s): claimed-card-from-worktree — resume or close before starting new work.
```

The hunter also reports the Stop hook half: with `pattern_generalization_check:
true` set only in the primary config, the hook exits 2 for `cwd` = primary and
0 for `cwd` = linked. Not re-run by the filing agent.

## Why it matters

Shared-deck mode is for one person working several branches against one queue.
That is the setup where a session opens in a worktree other than the one the
card was claimed from, and it is the setup where the reminder stays silent: the
agent is never told to resume or close the active card `goc` itself lists. The
OpenClaw port has the same gap, filed as
[openclaw-resolve-deck-dir-ignores-git-worktree-shared-deck-resolution](../openclaw-resolve-deck-dir-ignores-git-worktree-shared-deck-resolution/).
This is the Python side of the same omission, and one more instance of
[session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting](../session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting/).

## Falsification recipe

1. Build the layout above: the shared line uncommented and committed in the
   primary config, then a linked worktree.
2. From the linked worktree, create and claim a card with `goc`; confirm it
   lands in the primary deck.
3. Pipe `{"cwd": "<linked>"}` into `deck_session_start.py`. No `[GoC] Active
   card(s)` line confirms the hypothesis; the line disproves it.
4. Mind the config edit: appending a second `workflow:` block to the template
   config leaves the first one in force, so the redirect silently stays off.
   Uncomment the template's own line instead.

---
title: goc-migrate-runs-filesystem-operations-in-the-wrong-tree-under-shared-deck-worktree-mode
summary: "`goc migrate` resolves both deck trees from `REPO_ROOT` (engine.py:6123-6124) instead of `DECK_ROOT`, so under shared-deck-worktree mode it copies cards into the linked worktree's canonical tree and rmtree's the worktree's checkout copy of `deck/`, then prints \"Migration complete\" while the shared primary deck still carries the dual-tree conflict that every subsequent goc invocation refuses on. Same root cause the closed goc-move wrong-tree card fixed for git operations; migrate is the remaining filesystem-operation holdout."
status: open
stage: null
contribution: medium
created: "2026-07-06T01:18:22Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero (migrate run from a linked worktree under shared-deck mode merges into and removes the PRIMARY tree's decks, and the dual-tree conflict is gone for subsequent invocations)
  - [ ] TDD: `_cmd_migrate` resolves `canonical` and `legacy` from `DECK_ROOT` (engine.py:6123-6124), matching `_resolve_deck_dir` / `_git_auto_commit` / the fixed `goc move` path
  - [ ] MECHANICAL: the `_DUAL_TREE_CONFLICT` flag migrate's empty-legacy fall-through consults (engine.py:6185) agrees with the trees migrate now operates on
  - [ ] TDD: regression test covering the shared-deck-worktree migrate path (or a unit test asserting migrate's tree resolution uses `DECK_ROOT`)
  - [ ] PROCESS: full suite + `goc validate` clean
---

# goc-migrate-runs-filesystem-operations-in-the-wrong-tree-under-shared-deck-worktree-mode

`goc migrate` — the one verb exempted from the dual-tree refusal so it can
*fix* the conflict (`engine.py:3606`: `if _DUAL_TREE_CONFLICT and
args.command != "migrate"`) — resolves both trees it merges and deletes from
`REPO_ROOT` (the cwd) instead of `DECK_ROOT` (the tree the deck actually
lives in under shared-deck-worktree mode).

## Location

- `goc/engine.py:6123-6124` (`_cmd_migrate`):

  ```python
  canonical = REPO_ROOT / ".game-of-cards" / "deck"
  legacy = REPO_ROOT / "deck"
  ```

- Destructive step on the wrong tree: `goc/engine.py:6220`
  `shutil.rmtree(legacy)`.
- The invariant this violates is documented in the same file,
  `goc/engine.py:5420-5422`: "card_dir is always under DECK_DIR ⊆
  DECK_ROOT, which is NOT REPO_ROOT in shared-worktree-deck mode
  (DECK_ROOT is the primary tree, REPO_ROOT the linked worktree)."

## What's broken

In shared-deck-worktree mode (`GOC_WORKTREE_DECK=shared` or
`workflow.worktree_deck: shared`), `_resolve_deck_root`
(`engine.py:72-94`) points `DECK_ROOT` at the **primary** working tree so
all worktrees share one deck; `REPO_ROOT = Path.cwd()` (`engine.py:36`) is
the **linked** worktree. Every deck read and mutation goes through
`DECK_DIR ⊆ DECK_ROOT` — except `_cmd_migrate`, which builds both tree
paths from `REPO_ROOT`. Running `goc migrate` from a linked worktree whose
primary repo still carries a legacy `deck/` therefore:

1. copies legacy-only cards into the **worktree's** checkout copy of
   `.game-of-cards/deck/` (drift the shared deck never sees),
2. `rmtree`s the **worktree's** checkout copy of `deck/` (leaving the
   worktree dirty with deletions), and
3. prints `Migration complete. Run \`goc validate\` to confirm.` — while
   `DECK_ROOT` still has both trees, so `_DUAL_TREE_CONFLICT` re-arms and
   every subsequent goc invocation (including the suggested `goc validate`)
   keeps refusing with the dual-tree error migrate just claimed to fix.

The closed card
[goc-move-runs-git-operations-in-the-wrong-tree-under-shared-deck-worktree-mode](../goc-move-runs-git-operations-in-the-wrong-tree-under-shared-deck-worktree-mode/)
fixed the same root cause for `goc move`'s git operations and asserted move
was "the only deck-mutating verb" still running in `REPO_ROOT`. `goc
migrate` is the remaining holdout — via direct filesystem operations
(`copytree`/`rmtree`) rather than git subprocesses, which is why the
git-cwd sweep that closed that card did not catch it.

## Empirical evidence

`uv run python .game-of-cards/deck/goc-migrate-runs-filesystem-operations-in-the-wrong-tree-under-shared-deck-worktree-mode/reproduce.py`:

```
--- goc migrate (from linked worktree, shared deck mode) ---
Cards to migrate (legacy-only):
  deck/legacy-only-card/  →  .game-of-cards/deck/legacy-only-card/
  migrated: legacy-only-card

Removed legacy tree: /tmp/tmpt5_sezi0/linked/deck
Migration complete. Run `goc validate` to confirm.
Next: `goc validate` to verify card integrity after migration.

primary deck/ removed (expected True):        False
primary canonical got the card (expected True): False
worktree deck/ checkout deleted instead:      True
worktree canonical got the card instead:      True
subsequent goc still refuses on dual-tree:    True

DEFECT: migrate mutated the worktree's trees; shared deck untouched.
```

## Why it matters

Shared-deck-worktree mode is a shipped, documented feature (built by the
closed epic
[support-worktrees-and-multi-agent-deck-sync](../support-worktrees-and-multi-agent-deck-sync/));
its whole point is that agents run goc from linked worktrees. A consumer in
that mode whose repo still carries a legacy `deck/` gets the dual-tree
refusal on every verb, is told to run `goc migrate` — and migrate is the
one verb allowed through the refusal, yet it operates on the wrong tree,
reports false success, dirties the worktree with a deleted checkout tree
plus an unshared canonical copy, and leaves the shared deck exactly as
broken as before. There is no path out of the refusal loop from a linked
worktree.

Reachability: primary repo with both `.game-of-cards/deck/` and legacy
`deck/`, a linked `git worktree`, shared mode enabled, `goc migrate --yes`
from the worktree (see `reproduce.py`). Single-tree mode is unaffected
(`DECK_ROOT == REPO_ROOT` there).

## Fix

Mirror the `goc move` fix: resolve the trees `_cmd_migrate` merges and
deletes from `DECK_ROOT`, not `REPO_ROOT` —

```python
canonical = DECK_ROOT / ".game-of-cards" / "deck"
legacy = DECK_ROOT / "deck"
```

(`engine.py:6123-6124`). This is the same single-site substitution the
goc-move card applied to its git cwd, anchored by the documented invariant
at `engine.py:5420-5422`; note `_DUAL_TREE_CONFLICT` is already computed
against `DECK_ROOT`'s trees (`_resolve_deck_dir(DECK_ROOT)`,
`engine.py:123`), so migrate's own empty-legacy fall-through
(`engine.py:6185`) becomes self-consistent with the fix. Do NOT apply the
fix on this card's filing pass.

## Distinct from existing cards

- [goc-move-runs-git-operations-in-the-wrong-tree-under-shared-deck-worktree-mode](../goc-move-runs-git-operations-in-the-wrong-tree-under-shared-deck-worktree-mode/)
  (done) — same root cause, different verb and operation class (git cwd vs
  filesystem paths); its sweep covered `git` subprocess call sites only.
- [unrelated-deck-folder-trips-dual-tree-refusal-and-migrate-deletes-it](../unrelated-deck-folder-trips-dual-tree-refusal-and-migrate-deletes-it/)
  (open) — non-GoC `deck/` folders being mistaken for a legacy deck;
  orthogonal to which tree migrate resolves.
- [migrate-rmtrees-legacy-deck-without-confirm-when-it-has-no-card-dirs](../migrate-rmtrees-legacy-deck-without-confirm-when-it-has-no-card-dirs/)
  (done) and
  [goc-migrate-silently-destroys-card-files-other-than-readme-and-log](../goc-migrate-silently-destroys-card-files-other-than-readme-and-log/)
  (open) — migrate's confirm gate and merge scope, not tree resolution.

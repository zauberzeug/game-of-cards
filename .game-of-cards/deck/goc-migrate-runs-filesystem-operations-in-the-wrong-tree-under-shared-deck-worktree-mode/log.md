## 2026-07-07T01:36:53Z — Closure

- **What changed**: `goc/engine.py` (`_cmd_migrate`) — `canonical` and
  `legacy` now resolve from `DECK_ROOT` instead of `REPO_ROOT`, so under
  shared-deck-worktree mode migrate merges into and removes the primary
  tree's decks (the same trees `_resolve_deck_dir` computed
  `_DUAL_TREE_CONFLICT` against), not the linked worktree's checkout
  copies. Single-site mirror of the closed goc-move git-cwd fix.
- **Verification**: `reproduce.py` exits 1 before the fix (migrate mutated
  the worktree's trees, shared deck untouched, dual-tree refusal
  persisted), 0 after (`OK: migrate operated on the shared primary deck`).
  New regression test `tests/test_migrate_shared_worktree_tree_resolution.py`
  drives a real linked worktree + shared-deck migrate; verified it FAILS on
  the pre-fix code (temporary revert) and passes on the fix. The dual-tree
  refusal (`two deck trees found`) no longer fires from the worktree after
  migrate.
- **Audit**: PASS — no rubric configured; mechanical fix (tree-resolution
  alignment with the documented `DECK_DIR ⊆ DECK_ROOT` invariant,
  engine.py:5420-5422).
- **Project impact**: n/a
- **Tests**: 698 passed / 0 failed; `goc validate` clean; plugin mirrors
  re-synced via `scripts/sync_plugin_assets.py` (`--check` green).

## Closure verification (2026-07-07T01:37:15Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-07-07 — Closure' present

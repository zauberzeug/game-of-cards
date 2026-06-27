## 2026-06-27T00:00:00Z — Closure

- **What changed**: `goc/engine.py` — `_cmd_move`'s `git mv`,
  `_move_iter_tracked_text_files`'s `git ls-files` (+ rglob fallback and
  path joins), and `_move_preview_sites`'s `relative_to` now resolve to
  `DECK_ROOT` instead of `REPO_ROOT`, matching every other deck-touching
  git op. In shared-deck worktree mode the deck lives in the primary tree
  (`DECK_ROOT`), not the linked worktree the user runs from (`REPO_ROOT`).
- **Verification**: `reproduce.py` exits 1 before the fix (stale
  `title: old-card-slug` left in the moved card), 0 after. New regression
  test `tests/test_move_shared_worktree_git_cwd.py` drives a real linked
  worktree + shared-deck move and asserts a clean rename, rewritten title,
  and green `goc validate`.
- **Audit**: PASS — no rubric configured; mechanical fix (git-cwd
  alignment, single-site mirror of the existing `_git_auto_commit` pattern).
- **Project impact**: n/a
- **Tests**: 622 passed / 0 failed (plus plugin mirrors re-synced via
  `scripts/sync_plugin_assets.py`); `goc validate` clean.

## Closure verification (2026-06-27T01:20:16Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-06-27 — Closure' present

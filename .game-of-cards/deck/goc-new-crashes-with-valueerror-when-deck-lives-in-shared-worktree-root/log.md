## 2026-06-24T08:00:00Z — Closure

- **What changed**: `goc/engine.py:4917-4922` — `_cmd_new`'s success/next-step prints now display `card_dir.relative_to(DECK_ROOT)` (crash-proof, since `card_dir` is always under `DECK_DIR ⊆ DECK_ROOT`) instead of `relative_to(REPO_ROOT)`, which raised `ValueError` in shared-worktree-deck mode where `DECK_ROOT` (primary tree) != `REPO_ROOT` (linked worktree).
- **Verification**: reproduce.py exits 0 (was 1); new regression test `tests/test_new_shared_worktree_path_display.py` runs `goc new` from a real linked worktree with `GOC_WORKTREE_DECK=shared` and asserts no crash + card lands in the primary tree. Test fails on the pre-fix code (ValueError) and passes on the fix.
- **Audit**: PASS — no principle touched, mechanical fix (path-display consistency; mirrors the established `relative_to(DECK_ROOT)` pattern at engine.py:4291 and the `git_cwd = str(DECK_ROOT)` rationale at engine.py:4033-4036).
- **Project impact**: n/a
- **Tests**: full suite green after fix; plugin mirror parity green after `scripts/sync_plugin_assets.py`.
- **Bundled with**: none

## Closure verification (2026-06-24T07:43:00Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-06-24 — Closure' present

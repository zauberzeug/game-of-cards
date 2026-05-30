## 2026-05-30T01:26:07Z — Closure

- **What changed**: `goc/install.py:944` — switched the guard in `_append_precommit_hook` from `(target.parent / ".git").is_dir()` to `.exists()`, so git worktrees (where `.git` is a file containing `gitdir: …`) are correctly recognised as git checkouts. Plugin mirrors regenerated via `scripts/sync_plugin_assets.py`.
- **Verification**: `reproduce.py` exit 0 (post-fix writes `.pre-commit-config.yaml` in a worktree); `uv run python -m unittest discover -s tests` 243 passed (was 241, two new regression tests under `AppendPrecommitHookWorktreeTest`); `uv run goc validate` clean; `python scripts/sync_plugin_assets.py --check` green.
- **Audit**: PASS — no rubric configured; mechanical fix (file/directory shape detection — `.exists()` matches the original "is this a git checkout?" intent for both the regular-checkout `.git/` directory form and the worktree `.git` file form).
- **Project impact**: n/a
- **Tests**: 243 passed / 0 failed / 0 xfailed
- **Bundled with**: n/a

## Closure verification (2026-05-30T01:26:19Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-30 — Closure' present


## 2026-06-12T05:10:00Z — Closure

- **What changed**: `scripts/sync_plugin_assets.py` — the three per-name
  single-file hook pair loops (claude, codex, dogfood `.claude/hooks/`)
  became dir-syncs of `templates/hooks/` with `hooks.json` protected via
  `preserve_files`; `goc/engine.py` `validate_plugin_mirror_parity` — the
  per-name hook pairs became whole-directory pairs with `hooks.json`
  excluded, so dst-only stale hooks register as drift.
- **Verification**: reproduce.py exits 0 ("FIXED: orphaned hook files are
  pruned and --check flags stale ones."); stale hook pruned from all three
  flat mirrors; planted stale hook makes `--check` exit 1; hooks.json
  survives in both plugin hook dirs.
- **Audit**: PASS — no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: 429 passed / 0 failed (full suite, includes 5 new cases in
  tests/test_sync_hook_mirror_orphans.py and 4 new cases in
  tests/test_plugin_mirror_parity.py); `goc validate` exit 0;
  `sync_plugin_assets.py --check` OK on the clean tree.

## Closure verification (2026-06-12T05:00:46Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-06-12 — Closure' present

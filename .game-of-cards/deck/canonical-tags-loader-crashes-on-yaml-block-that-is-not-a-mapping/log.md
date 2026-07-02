## 2026-07-02 — Closure

Fixed `_load_consuming_repo_tags` (`goc/engine.py`) by adding an
`isinstance(block, dict)` guard immediately after `yaml.safe_load`, so a
fenced ```yaml block that parses to a non-mapping (a bare list, a
scalar) is skipped instead of `.get()`-ed. Before the guard, a
list-shaped block raised `AttributeError: 'list' object has no attribute
'get'`, and because `load_schema()` runs at module import
(`engine.py:2225`), the crash bricked every goc command with a raw
traceback.

Third instance of the canonical-tags defensive-loader family, orthogonal
to the two closed siblings (value-guard and element-guard) — under the
four-instance meta-fix threshold, filed as its own guard.

- reproduce.py: exit 1 (AttributeError) before → exit 0 (returns set())
  after.
- Added two regressions to `tests/test_consuming_repo_tags_loader.py`
  (non-mapping block skipped; non-mapping block does not poison a valid
  block). Full suite: 682 tests green after re-syncing plugin mirrors
  (`scripts/sync_plugin_assets.py` staged claude/codex/openclaw
  `goc/engine.py`).
- `uv run goc validate`: OK.

finish-card audit: PASS — no principle touched, mechanical fix (a
type-guard on a malformed-input path, matching the existing sibling
guard family). No project rubric configured (finish-card hook empty).

## Closure verification (2026-07-02T01:39:36Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-07-02 — Closure' present

## 2026-05-27T00:00:00Z — Closure

- **What changed**: `goc/engine.py` `parse_frontmatter` — replaced `safe_load(...) or {}` with an explicit `None → {}` / non-dict → `FrontmatterError` split, so a block-list/scalar frontmatter raises the coherent loader-contract error instead of a downstream `AttributeError`.
- **Verification**: reproduce.py exits 0 (all 3 non-mapping shapes coherent); `goc validate` on a deck with a list-frontmatter card reports `bad-card: frontmatter is not a mapping ...` and exits 1 (no traceback).
- **Audit**: PASS — restores the `parse_frontmatter` loader contract (api-contract); same FrontmatterError channel the unterminated-frontmatter card established.
- **Project impact**: n/a
- **Tests**: 174 passed / 0 failed (added NonMappingFrontmatterTest in tests/test_yaml_lite.py)
- **Bundled with**: plugin mirror re-sync (claude/codex/openclaw goc/engine.py)

## Closure verification (2026-05-27T13:54:46Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present

## 2026-05-27T08:27:03Z — Closure

- **What changed**: `goc/install.py` — added `_detect_newline` / `_read_text_keep_newline` / `_write_text_keep_newline`; routed `_append_marker_block`, `_strip_goc_block`, `_strip_claude_import`, `_sync_claude_import`, and `_append_precommit_hook` through them so an existing file's dominant line ending is preserved instead of forced to LF.
- **Verification**: reproduce.py now exits 1 (no defect) — 9 CR bytes preserved across the merge; LF-authored files stay LF (0 CR injected); `goc validate` exit 0.
- **Audit**: PASS — no project rubric configured; mechanical fix that restores the documented AGENTS.md "content outside markers preserved" byte-level guarantee.
- **Project impact**: n/a
- **Tests**: no pytest suite; reproduce.py + ad-hoc LF sanity check pass, `goc validate` clean.
- **Notes**: PROCESS sweep found two write-paths beyond the three named in the DoD — `_sync_claude_import` (CLAUDE.md marker-merge sibling) and `_append_precommit_hook` (CRLF `.pre-commit-config.yaml`) — both fixed. Plugin mirrors (claude/codex/openclaw) re-synced via scripts/sync_plugin_assets.py.

## Closure verification (2026-05-27T08:27:14Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present

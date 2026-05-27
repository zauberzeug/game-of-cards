## 2026-05-27T09:56:34Z — Closure

- **What changed**: `goc/install.py` — `_merge_claude_settings` parse-failure branch now backs up the original bytes to a timestamped `.bak` sibling (`_backup_unparseable_settings`) and warns on stderr before falling back to `{}`; `_strip_goc_settings_entries` warns instead of silently returning. Added `datetime` import.
- **Verification**: `reproduce.py` now exits 1 (was 0); backup sibling written containing the original malformed bytes; valid-JSON merge path unchanged (user keys preserved, no backup). `goc validate` OK.
- **Audit**: PASS — no project rubric configured; preserves the documented merge contract of `_merge_claude_settings` (mechanical data-loss fix).
- **Project impact**: n/a
- **Tests**: no pytest suite; reproduce.py + valid-path inline check pass.
- **Bundled with**: none

## Closure verification (2026-05-27T09:56:51Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present

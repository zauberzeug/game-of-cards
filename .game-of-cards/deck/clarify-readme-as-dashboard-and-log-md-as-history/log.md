## 2026-05-15T07:15:47Z — Closure

- **What changed**: `goc/templates/skills/{card-schema,create-card,advance-card,finish-card,deck}/SKILL.md` — replaced "narrative" framing with explicit **dashboard** (README) vs **append-only journal** (`log.md`) discipline; added a "What goes where" rule of thumb in `card-schema`, a transition routing table in `advance-card`, and Step-3-dashboard / Step-4-journal split in `finish-card`; `deck` Layout block mirrors the same framing.
- **Verification**: `uv run goc validate` clean (all cards OK); `uv run pytest -q` 119 passed; `python scripts/sync_plugin_assets.py --check` clean (claude-plugin + openclaw-plugin + `.claude/` mirrors byte-for-byte match goc/templates).
- **Audit**: PASS — no rubric configured; mechanical doc-prose fix (writing-contract clarification, no engine or schema change).
- **Project impact**: n/a
- **Tests**: 119 passed / 0 failed / 0 xfailed
- **Bundled with**: none

## Closure verification (2026-05-15T07:16:12Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 8/8 ticked
- [x] log-md-closure-entry — '## 2026-05-15 — Closure' present

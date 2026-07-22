## 2026-07-22T13:45:00Z — Closure

- **What changed**: `goc/templates/skills/card-schema/reference.md:68` and `goc/templates/skills/create-card/reference.md:96` — the draft-hiding contract now cites `goc --ready` instead of the nonexistent `goc next` verb; all mirror trees regenerated (claude/codex/openclaw plugin skills + `.claude/skills` / `.codex/skills` dogfood copies).
- **Verification**: `python scripts/sync_plugin_assets.py --check` and `python3 scripts/port_skills_to_openclaw.py --check` both clean; `grep -rn "goc next"` has zero hits outside historical deck card bodies.
- **Audit**: PASS — no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 752 passed / 0 failed

## Closure verification (2026-07-22T13:25:49Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-07-22 — Closure' present

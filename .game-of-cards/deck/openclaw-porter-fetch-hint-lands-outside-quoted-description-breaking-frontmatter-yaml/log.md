## 2026-07-23T13:40:00Z — Closure

- **What changed**: scripts/port_skills_to_openclaw.py — `_hint_into_description()` inserts the fetch hint inside quoted description scalars with YAML quote escaping (`"` → `\"`, `'` → `''`); plain scalars keep the line append. Re-ported openclaw-plugin/skills/ (pull-card, next-card frontmatter now one complete quoted scalar). tests/test_skill_frontmatter_strict_yaml.py — `_quoted_scalar_hazard()` flags trailing content after a closing quote and unterminated quoted scalars; unit test covers the exact pre-fix shape.
- **Verification**: reproduce.py pre-fix printed 2 [FAIL] (pull-card, next-card), post-fix exits 0 with 16/16 clean; the strengthened hazard scan flags the HEAD payload ("content after closing quote") and is clean on the fixed tree; port_skills_to_openclaw.py --check OK; sync_plugin_assets.py --check OK.
- **Audit**: PASS — no rubric configured; mechanical fix
- **Project impact**: published OpenClaw payload regains loadable pull-card and next-card skills; the strict-YAML guard now covers quoted scalars across all six shipped skill roots.
- **Tests**: 759 passed / 0 failed

## Closure verification (2026-07-23T13:23:48Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-07-23 — Closure' present

## 2026-05-26T00:00:00Z — Closure

- **What changed**: `openclaw-plugin/skills/card-schema/SKILL.md` — re-ported from `goc/templates/skills/card-schema/SKILL.md` via `scripts/port_skills_to_openclaw.py`, picking up the ready-predicate `not waiting_impedes(card)` rewrite and the `Underscores` title-antipattern table row.
- **Verification**: porter touched 1 file; `--check` exits 0; drift guard test now green.
- **Audit**: PASS — no principle touched, mechanical fix.
- **Project impact**: n/a
- **Tests**: 12 passed / 0 failed / 0 xfailed (`tests.test_plugin_mirror_parity`)
- **Bundled with**: none

## Closure verification (2026-05-26T23:52:07Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present

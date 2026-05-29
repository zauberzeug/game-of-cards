## 2026-05-29T13:12:40Z — Closure

- **What changed**: `goc/templates/skills/next-card/SKILL.md:21,45,137`, `goc/templates/skills/deck/SKILL.md:130`, `goc/templates/skills/audit-deck/SKILL.md:67` — replaced "impact-sorted"/"sorted by impact"/"Impact ladder"/"impact, why" with engine vocabulary ("value-sorted"/"sorted by value"/"Contribution ladder"/"contribution, why").
- **Verification**: `reproduce.py` exit 0; drift hits 5 → 0; engine 'impact' token count remains 0.
- **Audit**: no rubric configured; mechanical fix (terminology realignment to match engine source-of-truth).
- **Project impact**: n/a
- **Tests**: reproduce.py exit 0; `sync_plugin_assets.py --check` clean; `port_skills_to_openclaw.py --check` clean; `goc validate` clean on this card.

## Closure verification (2026-05-29T13:12:50Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 7/7 ticked
- [x] log-md-closure-entry — '## 2026-05-29 — Closure' present

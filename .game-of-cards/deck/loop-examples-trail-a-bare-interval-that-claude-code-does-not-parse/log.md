## 2026-10-08T04:47:59Z — Closure

- **What changed**: `goc/templates/skills/pull-card/SKILL.md:184` and `goc/templates/skills/deck/reference.md:67` — `/loop pull-card 30m` became the documented interval-first `/loop 30m /pull-card`. Mirrors were regenerated, and a new guard was added: `tests/test_loop_examples_lead_with_the_interval.py`. Fix-through, surfaced while closing `kickoff-autonomy-choice-hands-off-to-host-complements-that-carry-no-recipe`.
- **Verification**: `reproduce.py` found 2 offenders (exit 1) before the fix and none (exit 0) after. The test's detector flags the pre-fix `pull-card` text read from `HEAD`. `sync_plugin_assets.py --check` and `port_skills_to_openclaw.py --check` are clean, and `goc validate` exits 0.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1250 passed / 0 failed (`uv run python -m unittest discover -s tests`; 2 new)
- **Bundled with**: none

## Closure verification (2026-10-08T04:47:59Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-10-08 — Closure' present

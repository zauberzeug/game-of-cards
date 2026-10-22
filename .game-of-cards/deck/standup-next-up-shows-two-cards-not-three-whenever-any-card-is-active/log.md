## 2026-09-16T05:24:47Z — Closure

- **What changed**: `goc/templates/skills/standup/SKILL.md:115` — Section 5 filters the engine's conditional `ACTIVE:` stdout banner (`grep -v '^ACTIVE:'`) before its fixed `head -5`, so the 5-line budget buys 2 lines of table chrome plus the 3 rows the prose promises instead of 3 lines of chrome plus 2 rows. Prose gained a paragraph naming why the filter is there and why the budget stays at 5. Five mirrors regenerated; `tests/test_standup_next_up_row_budget.py` added.
- **Verification**: `reproduce.py` 1 → 0; scratch deck with an active card went 2/3 → 3/3 promised rows, deck without stayed 3/3. On this repo's live deck (7 active, empty ready queue) the fixed command emits the zero-match line unchanged, so the filter does not swallow the empty-queue report. The new guard failed on all 5 mirrors before the sync run and passes after.
- **Audit**: PASS — no rubric configured (`.game-of-cards/hooks/finish-card.md` is empty); mechanical fix to a shipped skill's shell block plus its explanatory prose.
- **Project impact**: standup's only forward-looking section stops silently dropping a third of its rows whenever any card is claimed — which on this deck is every session.
- **Tests**: 1157 passed / 0 failed (was 1155; +2 from the new guard). `uv run goc validate` clean; `scripts/sync_plugin_assets.py --check` and `scripts/port_skills_to_openclaw.py --check` both clean.
- **Bundled with**: n/a

## Closure verification (2026-09-16T05:24:50Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-09-16 — Closure' present

## 2026-09-16T05:02:24Z — Closure

- **What changed**: `goc/templates/skills/standup/SKILL.md:22` — the Section 2 Context block queries `--json --status all` instead of `--json --status open`, and re-narrows with `live_impeded`'s two liveness conjuncts (non-terminal status, non-draft). Section 2's prose gained one sentence naming that scope. The `waiting_on`-truthiness predicate was deliberately left alone.
- **Verification**: `reproduce.py` exits 1 before / 0 after. On the live deck the block now reports the same 4 titles as `goc --waiting`, up from 3 — the recovered card is `openclaw-plugin-skills-force-repeated-reads-every-session` (active + `waiting_on: external`). 3 of the 4 new assertions in `tests/test_standup_impeded_block_scope.py` fail against the pre-fix template, so the guard catches the offender rather than only agreeing with the fix.
- **Audit**: no rubric configured; mechanical fix — `.game-of-cards/hooks/finish-card.md` is an empty stub.
- **Project impact**: n/a
- **Tests**: 1155 passed / 0 failed (was 1151); `goc validate`, `scripts/sync_plugin_assets.py --check` and `scripts/port_skills_to_openclaw.py --check` all clean.
- **Bundled with**: none

## Closure verification (2026-09-16T05:02:27Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-09-16 — Closure' present

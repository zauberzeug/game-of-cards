## 2026-08-23T05:05:00Z — Closure

- **What changed**: `goc/templates/skills/standup/SKILL.md:113` — Section 5
  ("Next up") selects with `goc --ready` instead of bare `goc`, so the
  forward look shows the cards `Skill(pull-card)` would actually pick.
  Two prose additions ship with it: the four conjuncts `--ready` applies
  (so the flag is not lost in a future rewrite), and an exception to the
  "omit empty sections" rule so a dry queue is reported rather than
  hidden. Five mirrors regenerated from the template; nothing else
  hand-edited.
- **Verification**: `reproduce.py` exits 0 (was 1). On its scratch deck the
  pre-fix predicate scored 3/3 false positives and 1 false negative; the
  post-fix predicate scores 0 and 0. On this repo's own deck the section
  now reports "No cards match (ready: ...)" instead of three
  `human_gate: session` epics. `tests/test_standup_next_up_predicate.py`
  was observed failing on the pre-fix mirrors before they were synced, so
  the guard is a real tripwire.
- **Audit**: PASS — no rubric configured
  (`.game-of-cards/hooks/finish-card.md` is an empty stub); mechanical
  substitution of a documented engine predicate for a hand-rolled subset.
- **Project impact**: n/a
- **Tests**: 1030 passed / 0 failed; `uv run goc validate` clean;
  `scripts/sync_plugin_assets.py --check` and
  `scripts/port_skills_to_openclaw.py --check` both clean.
- **Bundled with**: n/a

## Closure verification (2026-08-23T04:56:55Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-08-23 — Closure' present

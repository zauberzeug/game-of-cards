## 2026-09-19T04:39:58Z — Closure

- **What changed**: `goc/templates/skills/standup/SKILL.md:88-119` — Section 4
  queries `--status all` and re-narrows with the two liveness conjuncts
  (non-terminal, non-draft) instead of `--status open`, so a card claimed and
  then parked behind a raised gate reaches the view that exists to surface it.
  Prose gained a paragraph naming the scope, mirroring Section 2.
- **Verification**: `reproduce.py` 1 → 0 (the two `active`+gated grid cells
  flipped to reported, the ungated / terminal-stale-gate / draft controls stay
  omitted). On this repo's deck the section reports 197 live gated cards, up
  from 192 — the 5 recovered are exactly the parked-active cards the
  SessionStart hook already names. Guard sensitivity: 2 of the 4 new tests fail
  against the pre-fix template.
- **Audit**: no rubric configured; mechanical fix
  (`.game-of-cards/hooks/finish-card.md` is an empty stub).
- **Project impact**: n/a
- **Tests**: 1161 passed / 0 failed / 0 xfailed (was 1157; +4 from
  `tests/test_standup_waiting_on_you_block_scope.py`). `goc validate` clean.
- **Filed as an instance, not a point-fix proposal**: wired
  `advances: active-state-conflates-being-worked-on-with-parked-at-human-gate`.
  That root card's three options all land a Python predicate; this caller is a
  shell pipeline in a skill body with no import path, so no helper shape reaches
  it. Same reasoning recorded for Section 2 on
  `waiting-impedes-callers-reimplement-the-terminal-status-liveness-gate-and-drift`
  three days earlier. The architecture stays the human's call.

## Closure verification (2026-09-19T04:39:59Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 7/7 ticked
- [x] log-md-closure-entry — '## 2026-09-19 — Closure' present

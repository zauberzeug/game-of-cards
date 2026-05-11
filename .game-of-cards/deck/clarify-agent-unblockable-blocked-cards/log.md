## 2026-05-11 — Closure

Documented the orthogonality of `status` and `human_gate` across three
GoC skills:

- `card-schema/SKILL.md` — extended the status table's `blocked` row
  to note that agent-checkable external conditions keep
  `human_gate: none`; added a new opening paragraph to the "human_gate
  scale" section stating that `status` and `human_gate` are orthogonal
  axes; expanded the `none` bullet to cover the parked-but-agent-
  unblockable case; added a closing paragraph restricting
  `decision`/`session` to human-judgement blockers.
- `advance-card/SKILL.md` — added an orthogonality reminder in Step 1
  (read-the-card), and extended the Step 2 transition table:
  `active → blocked` notes when to keep `human_gate: none`,
  `blocked → active` notes that an autonomous agent MAY re-flip when
  the observed condition clears, and a new `blocked → open` row
  documents the analogous re-queue transition.
- `deck/SKILL.md` — added a paragraph after the lifecycle prose
  noting that `status: blocked` and `human_gate` are orthogonal, with
  cross-reference to `Skill(card-schema)`.

Templates under `goc/templates/skills/...` are the source of truth;
the consumer copies under `.claude/skills/` and `.codex/skills/`
were updated in lockstep per the CLAUDE.md dogfooding rule.

`goc validate` passes on the full deck.

## Closure verification (2026-05-11)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-11 — Closure' present

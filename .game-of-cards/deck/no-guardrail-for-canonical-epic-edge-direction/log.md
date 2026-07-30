## 2026-05-26T06:30:00Z — Closure

- **What changed**:
  - `goc/engine.py` — added `validate_epic_edge_direction()` (advisory
    `BACKWARDS_EPIC_EDGE` hint, contribution-gradient heuristic, never
    contributes to validate's exit code) and wired it into
    `_cmd_validate` alongside the existing blocker/waiting warnings.
  - `goc/templates/skills/card-schema/SKILL.md` — new subsection
    "Coordinating cards — aggregation epic vs governing cluster"
    documenting the three-way fork (aggregation epic → edge,
    governing cluster → tag, backwards → bug). Cross-reference to
    `advanced-by-treated-as-hard-prerequisite-…` (Option E) added to
    the "Value-chain rule" subsection so a reader who hits
    `advanced-by-closed` FAIL lands on the value-chain reasoning.
  - `goc/templates/skills/create-card/SKILL.md` — Step 4 expanded
    with the three-way fork at the point an edge is authored,
    naming the `--gate decision` tell for governing clusters.
  - `.game-of-cards/deck/no-guardrail-for-canonical-epic-edge-direction/reproduce.py`
    — exercises engine pure functions (`_run_derived_check`,
    `validate_epic_edge_direction`) against fixtures for all three
    shapes; asserts canonical PASS + lint silent, backwards FAIL +
    lint fires, governing-cluster both edge directions broken, tag
    encoding clean.
- **Verification**:
  - `uv run python .game-of-cards/deck/no-guardrail-for-canonical-epic-edge-direction/reproduce.py`
    → all three shapes behaved as documented; all assertions pass.
  - `uv run goc validate --quiet` → no new errors on this repo's
    deck. `BACKWARDS_EPIC_EDGE` did NOT fire on the canonical
    aggregation epic `blocked-status-conflates-…` (which uses
    `advanced_by: [children]` with empty `advances`).
  - `advanced-by-closed` derived check at `goc/engine.py:2960` was
    read and left unchanged; the lint is additive, not a
    modification of the closure gate.
- **Audit**: PASS — no rubric configured (`.game-of-cards/hooks/finish-card.md`
  is the unedited template); the closure aligns with the documented
  GoC convention (`Skill(card-schema)`'s value-chain rule) by
  surfacing the canonical edge direction at authoring time and
  detecting the inversion without modifying the closure gate.
- **Project impact**: card-schema and create-card skill bodies now
  state the three-way fork in-line; `goc validate` carries a new
  advisory `BACKWARDS_EPIC_EDGE` hint with a shape-sensitive fix
  suggestion (flip vs. tag).
- **Tests**: no pytest suite exists in this repo; reproduce.py is the
  behavioral verification (all assertions pass).
- **Bundled with**: none.

## Closure verification (2026-05-26T06:01:45Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present

## 2026-07-30 — Later evidence: the shared-tag prescription is unreachable by traversal

This card's governing-cluster shape — a decision card groups its cluster with a shared
tag and no `advances` edge, because no edge direction models the relationship without
deadlocking or contradicting the decision's independence — is unchanged and still
correct.

New evidence about a consequence it did not name. A tag is invisible to every edge walk
in the tool, so following this guidance correctly makes the cluster unreachable from any
card inside it. Observed in a consuming repository: a governing card retracted its seven
grouping edges so `goc done` would accept it, regrouped by tag as prescribed, and became
unfindable. The tag accumulated 22 cards; a later umbrella card on the same subject cited
none of them and re-derived results already measured and closed. `goc validate` was clean
throughout, because referential integrity proves the edges that exist resolve and cannot
see a grouping that has no edges.

Filed as [[a-shared-tag-groups-a-cluster-that-no-edge-walk-can-reach]], which states the
problem and sketches five options without deciding. No action is owed by this card.

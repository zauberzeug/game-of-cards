## 2026-05-23T04:02:33Z: card filed — decision options enumerated

Archived here because `goc decide` replaces the `## Decision required`
section in README without preserving the previous content. README is
the dashboard (current state); log.md is the journal (history). This
entry recovers the deliberation that produced the decision below.

The card was filed at `human_gate: decision` with four options in the
`## Decision required` section:

### Option A — Full mirror of audit-deck's discipline (largest blast radius)

Three coordinated edits to `goc/templates/skills/refine-deck/SKILL.md`:

1. Replace line 36 framing with a filing-authorisation principle
   ("every candidate this skill surfaces is filed this round; chat
   output and scratch files are NOT durable slots").
2. Add a Step 4.5 pre-commit disposition audit mirroring `audit-deck`'s
   Phase 3 "Park-or-disprove unfollowed candidates (mandatory)". The
   audit scans the commit plan for deferral phrases ("deferred to
   follow-up", "user decides which to land", "surface as proposals")
   and routes them back to filing.
3. Rewrite Step 2 / Step 3 recommendations as imperative for cards:
   canonical-tag and contribution-recall stay as **proposal-cards**
   (preserving the "human decides the policy" property), but the
   proposal-card itself is filed via
   `Skill(create-card) ... --gate decision`.

Most coherent symmetry with `audit-deck`. Largest text-change in the
skill body.

### Option B — Step 4.5 audit only (minimal)

Preserve the line 36 "propose, don't apply" framing but add a
mandatory Step 4.5 disposition-audit checklist. Same checklist
semantics as Option A's #2, no other changes.

Smallest blast radius. Risk: the Step 1 / Step 3 framing tone still
biases the agent toward proposal stance before Step 4.5 corrects, so
agents may produce a commit plan that the audit then has to bounce —
slower convergence than Option A.

### Option C — Per-category disposition rules (recommended)

Replace the unified "propose, don't apply" with explicit per-category
rules in the skill body:

- **Hygiene** (stale parks, defunct cites, missing summaries,
  predicate-failing tags, orphaned-edge sub-checks): apply
  mechanically. Current behaviour.
- **Schema-touching** (new canonical tags): propose-only via
  SCHEMA.md PR. Current behaviour for Step 3.
- **Structural** (epic-shaped clusters, meta-decision umbrellas,
  missing canonical-reference families, contribution-recall
  proposals): file as a card via `Skill(create-card)`; use
  proposal-cards (`*-canonical-tag-proposal`,
  `contribution-recalls-from-<date>-refine-deck-pass`, both
  `--gate decision`) when the finding requires a human policy pick
  to land.

Most precise fix. Surgically separates the three legitimate
disposition rules and matches the actual taxonomy of findings the
skill surfaces. Largest skill-body restructuring (rewrites the
framing line + adds a taxonomy section), but no new text in Step 4.

### Option D — Defer

Wait for additional downstream reports before changing shipped
behaviour. Risk: every refine-deck round on a
structural-pattern-discovery-extended hook continues to drop findings
until the discipline ships.

### Agent recommendation

Option C — surgically matches the three legitimate disposition rules
to the three actual finding-class shapes. Option A was the close
second; trade-off was text volume (A adds a whole new Step 4.5;
C restructures the existing framing line + adds a 3-bullet taxonomy).

## 2026-05-23T04:49:36Z: decision recorded

Apply Option A — full mirror of audit-deck Phase 3 discipline (rewrite framing as filing-authorisation + add Step 4.5 pre-commit disposition audit + rewrite Step 2/3 recommendations as imperative for cards) — Maximum symmetry with audit-deck's mature Park-or-disprove discipline preferred over the per-category-rules recommendation; chosen by user. Gate decision → none.

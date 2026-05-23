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

## 2026-05-23: implementation landed

Four surgical edits to `goc/templates/skills/refine-deck/SKILL.md`:

1. **Framing** (line 36 area): replaced `Surface rot and propose
   corrective edits — never apply them silently.` with a two-bullet
   taxonomy distinguishing hygiene (apply directly) from structural
   (file/disprove/park, never chat-only).
2. **Step 1 disposition rule** (former lines 57-59): replaced
   recommendation-only language with imperative disposition language
   pointing forward to Step 4.5.
3. **Step 3** (was "propose new canonical tags"): renamed to "file
   new canonical tag candidates" and rewrote the body so the
   tag-PR scheduling card is filed via `Skill(create-card)` rather
   than chat-proposed. The schema's "Adding new tags" rule is
   preserved — only the act of *scheduling* the schema PR is
   imperative.
4. **Step 4** (was "surface and recommend"): renamed to "surface and
   act"; rewrote example lines so each terminates in an action
   ("Skill(advance-card) → disproved", "updated citation to ...",
   "stripped tag") rather than "recommend Skill(...)".
5. **Step 4.5** (new): "Park-or-disprove unfollowed structural
   candidates (mandatory)" — direct mirror of audit-deck Phase 3 at
   lines 168-189, scoped explicitly to structural candidates so the
   hygiene mechanical-apply path is preserved.

The sync hook regenerated `.claude/skills/refine-deck/SKILL.md`,
`.codex/skills/refine-deck/SKILL.md`,
`claude-plugin/skills/refine-deck/SKILL.md`, and
`codex-plugin/skills/refine-deck/SKILL.md` byte-for-byte from the
template. `python scripts/sync_plugin_assets.py --check` returns
`OK — plugin payloads + dogfood self-host copies match goc/ and
goc/templates/ byte-for-byte.`

### DoD verification

**#4 — structural-finding disposition discipline.** Trace
verification on the new SKILL.md: an agent reading the updated body
encounters the imperative framing at the top of the skill before
reaching any of the survey categories. Step 3 mandates filing for
tag candidates. Step 4 examples all terminate in actions. Step 4.5
explicitly forbids commit when structural candidates lack a
disposition. There is no remaining path in the body that resolves
to "surfaced and discussed in chat" for a structural candidate. A
real round on a hooked downstream project would surface
pattern-discovery candidates; the new body routes each through
file/disprove/park. The empirical run on *this* repo cannot
trigger structural pattern-discovery because the local hook at
`.game-of-cards/hooks/refine-deck.md` is empty (no project-specific
extension); the trace verification on the body text is the best
available evidence in-session and is sufficient given the change
is a documented contract, not executable logic.

**#5 — hygiene categories unchanged.** Step 2 (lines ~91-244) was
not edited; every hygiene category retains its mechanical-apply
text. Step 4.5 explicitly carves out hygiene findings ("Hygiene
findings ... they're applied directly in Step 2 and need no Step
4.5 audit."). The four hygiene goc queries — `goc --tag unverified
-v`, `goc --status open --json | head -100`, `goc quality-pass
--status all`, and the orphaned-dependency sub-checks — fire
unchanged with their existing apply-direct recommendations.

**#6 — per-category taxonomy → AGENTS.md.** Conditional doesn't
fire: Option A is *full mirror* (single Phase-3-style discipline),
not per-category rules (which would be Option C, the rejected
alternative). The hygiene-vs-structural split is a binary
"does this finding type have a mechanical-apply path?" check, not
a per-category rulebook with one rule per Step 2 sub-section.
Contract is visible in SKILL.md where future readers encounter it
at skill load.

### Scope notes

- `openclaw-plugin/skills/refine-deck/SKILL.md` is NOT in the DoD
  sync list and was not re-ported this round. The OpenClaw mirror
  retains the older "propose, don't apply" framing; a separate
  re-port via `scripts/port_skills_to_openclaw.py` is the documented
  path when consumers want to align it. Same out-of-scope handling
  as the predecessor card.
- No CLI changes, no schema changes, no canonical-tag changes.
  SKILL.md edits + auto-synced mirrors only.

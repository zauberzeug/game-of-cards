# Log

## 2026-05-23T05:06:53Z: Decision required (archived at filing)

Archived from README's `## Decision required` section before `goc decide` replaced it with the resolved `## Decision` block, so the deliberation (options + recommendation + trade-offs) survives the dashboard rewrite. Manual application of the `goc-decide-loses-deliberation-history-by-not-archiving-replaced-section` fix (Option A), per the workaround precedent in commit `674cc5e`.

Three credible scopes for the fix.

### Option A — decide-card-only guidance (minimum viable)

Add a subsection to `goc/templates/skills/decide-card/SKILL.md` (under Workflow Step 1 or as a new Step 1.5) prescribing:

> When the card's body has a `## Decision required` section with labeled options (Option A, Option B, ...), the `AskUserQuestion` payload uses the source's labels and order verbatim. Mark the recommendation in-place by appending `(Recommended)` to the existing label (e.g., `"Option C: Per-category rules (Recommended)"`). Do not reorder for the AskUserQuestion tool description's "recommended first" guidance — that convention applies only to ad-hoc questions where labels don't pre-exist in a source artifact.

Pros: narrow scope, single SKILL.md edit, fixes the confirmed-defect surface. Auto-syncs to the four mirror copies via `scripts/sync_plugin_assets.py`.

Cons: the same convention will likely need replication in sibling skills (pull-card, advance-card, scan-deck's interactive walks) the next time they hit the same bridge. Risk of guidance drift across skills.

### Option B — Replicate in sibling skills

Same prescription as Option A, but applied to every skill that bridges card-body options to `AskUserQuestion`: decide-card, pull-card, advance-card, scan-deck.

Pros: closes the gap consistently across the skill set.

Cons: significant text duplication across 4+ skill bodies. Future skills will need to remember to include the same prescription. Replicated prose drifts.

### Option C — `card-schema`-level convention (recommended)

Add the prescription to `goc/templates/skills/card-schema/SKILL.md` as a general "bridging card options to user-facing pickers" convention. Other skills cite it via cross-reference rather than duplicating the prose.

Justification: card-schema is the existing home for cross-skill conventions (canonical tags, status enums, DoD format, the decision-gate body contract). The "how to elicit a user pick from a card-body's labeled options" rule is structurally a sibling of the existing "## Decision required body contract" rule already documented there.

Pros: single source of truth, citeable from any skill that needs the discipline, future skills get the convention free by reading card-schema.

Cons: adds a UI-rendering rule to a schema-documentation skill (mild scope creep). The card-schema skill is currently about data shape; this rule is about presentation. Could feel out-of-place.

### Option D — Defer

No change. Continue to rely on agent judgement / per-session memory for AskUserQuestion mirroring. Risk: every fresh decide-card invocation in a session without the relevant memory loaded will repeat the defect.

### Recommendation

Option C. card-schema is the right home for cross-skill conventions, the existing "decision-gate body contract" rule is the closest sibling, and citing it from the skill bodies that need it keeps the prose single-source. Option A is the close second if Option C feels like scope creep into presentation rules.

## 2026-05-26T12:10:35Z: decision recorded

Option A — decide-card-only guidance. Add a Workflow Step 1.5 to the decide-card SKILL.md: when a card body has a labeled Decision-required section, the AskUserQuestion payload uses the source labels and order verbatim and marks the recommendation in-place with (Recommended), overriding the tool recommended-first guidance for this bridging case. — Narrow scope, single SKILL.md edit, fixes the confirmed-defect surface, and auto-syncs to the four mirror copies. The recommended Option C (card-schema convention) was passed over as scope creep of a presentation rule into a schema-documentation skill; revisit C if the same bridge recurs in sibling skills.. Gate decision → none.

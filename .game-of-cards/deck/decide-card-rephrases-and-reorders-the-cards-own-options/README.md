---
title: decide-card-rephrases-and-reorders-the-cards-own-options
summary: "When `Skill(decide-card)` bridges a card body's labeled `## Decision required` options (Option A/B/C/D) to an `AskUserQuestion` picker, the skill body offers no guidance on preserving source-option labels or order. Agents follow the tool-level `recommended first` heuristic and reorder/rephrase, which forces the user to mentally remap their pick between two presentations. Scope decision needed: decide-only guidance, sibling skills too, or a `card-schema`-level convention."
status: open
stage: null
contribution: medium
created: "2026-05-23T05:06:53Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] `goc/templates/skills/decide-card/SKILL.md` includes a subsection (under "Workflow" Step 1 or as a new Step 1.5) prescribing: when the card has labeled options in `## Decision required`, the `AskUserQuestion` payload uses the source's labels and order verbatim; mark the recommendation in-place by appending `(Recommended)` to the existing label; do not reorder for "recommended first."
  - [ ] The prescription explicitly overrides the `AskUserQuestion` tool description's "make recommended option first" guidance for this bridging case.
  - [ ] If the scope decision picks Option B below (sibling skills), the prescription is replicated in or referenced from any other skill that bridges card-body options to `AskUserQuestion`.
  - [ ] If the scope decision picks Option C below (`card-schema`-level), the rule lives in `goc/templates/skills/card-schema/SKILL.md` as a general "bridging card options to user-facing pickers" convention; other skills cite it.
  - [ ] An autonomous decide-card invocation on a card with labeled `## Decision required` options demonstrates verbatim mirroring in the elicited picker — verifies the discipline change took.
---

# decide-card-rephrases-and-reorders-the-cards-own-options

## Location

`goc/templates/skills/decide-card/SKILL.md` — Workflow Step 1 says "Read the card body. Confirm the decision the user is making actually answers the parked question." Step 2 says "Run `goc decide --decision ... --because ...`." There is no guidance between Step 1 and Step 2 for how to elicit the user's choice when the card body presents labeled options — agents fall back to ad-hoc `AskUserQuestion` calls following the tool description's generic guidance.

## What's broken

When `Skill(decide-card)` is invoked on a card whose body has a `## Decision required` section with labeled options (Option A, Option B, Option C, Option D), the natural agent move is to call `AskUserQuestion` to elicit the user's pick. The `AskUserQuestion` tool description says:

> If you recommend a specific option, make that option the first option in the list and add `(Recommended)` at the end of the label.

That guidance is correct for ad-hoc questions where labels don't pre-exist anywhere. It is **wrong** when the options pre-exist as a labeled enumeration in a source artifact (the card body), because reordering breaks the user's ability to map their pick onto the source's labels.

The decide-card SKILL.md doesn't override this. So agents follow the tool description's guidance, reorder for "recommended first," and the user — who reads "Option A" in the card body and types "Do option A" — has to mentally remap because the picker presented their Option A as item #2 (or wherever it landed under the reorder). The reorder is the primary defect; the parallel rephrasing of labels (from the card's prose format to AskUserQuestion's terser 1-5-word label constraint) compounds it by adding a second remap layer.

## Empirical evidence

The just-completed `Skill(decide-card)` invocation on the predecessor card `refine-deck-drops-structural-findings-by-defaulting-to-propose-not-file` exhibited this. The card body presented options in A/B/C/D order with Option C marked as recommended. The agent's `AskUserQuestion` payload reordered to put C first (following the "recommended first" tool guidance) and rephrased the labels to fit AskUserQuestion's terser format. The user replied "Do option A" — which required disambiguating: was that AskUserQuestion item #1 (Per-category rules) or card body Option A (Mirror audit-deck fully)? The card body's labels are canonical; the user meant Option A from the card. The reorder created friction where there should have been none.

User feedback (synthesised): the picker should help the user quickly orient to the situation. Instead, the reorder + rephrase forced a remap layer that defeated the picker's purpose. The decision skill should make picking easier, not harder.

## Why it matters

- **Lazy-Andon UX violation.** The decide-card skill's whole purpose is to make lowering the cord cheap (per the Andon-cord metaphor in the skill's preamble). When the picker requires the user to maintain a mental map between two presentations, the cord-lowering action stops being cheap — and workers route around expensive cords.
- **Skill prescribes a UI but doesn't prescribe how to render it.** decide-card's body describes the workflow (read card → run `goc decide`) but the elicitation step in the middle is undocumented. Agents fill the gap with the AskUserQuestion tool's generic conventions, which weren't designed for the source-artifact-already-has-labels case.
- **Recurring pattern across skills.** Any skill that asks the user to pick from labeled options in a card or doc has this risk: pull-card when choosing between conflicting next-actions, advance-card when offering status flips, scan-deck's decision Q&A walks, and any hypothetical future skill that elicits a user choice from pre-labeled options. The discipline gap is in the bridging convention, not in any single skill.

## Decision required

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

## Notes on fix scope

The fix is **documentation-only** — no engine change, no schema change, no CLI change. Lands as edits to one or more skill bodies in `goc/templates/skills/`, auto-synced to the four mirror copies via `scripts/sync_plugin_assets.py`.

The prescription is **additive**: agents that already mirror source options verbatim (e.g., via the just-saved feedback memory in this conversation) continue to work. Agents that previously followed AskUserQuestion's "recommended first" guidance get corrected.

## Cross-references

- Sibling card: [goc-decide-loses-deliberation-history-by-not-archiving-replaced-section](../goc-decide-loses-deliberation-history-by-not-archiving-replaced-section/) — the parallel engine-side decide-card defect (log.md doesn't preserve the deliberation that this card's options drove). Same root: decide-card workflow has UX gaps that surfaced together.
- AskUserQuestion tool description — Claude Code's built-in tool. Out of scope to change directly; this card patches the goc-side discipline to override the tool's generic guidance for the source-artifact-has-labels case.
- Convention reference: `Skill(card-schema)` "Decision-gate body contract" subsection — the closest sibling to the proposed new convention, currently the only cross-skill rule about how `## Decision required` sections render.

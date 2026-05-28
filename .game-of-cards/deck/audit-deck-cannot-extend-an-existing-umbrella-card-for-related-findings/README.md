---
title: audit-deck-cannot-extend-an-existing-umbrella-card-for-related-findings
summary: "When `audit-deck` finds a defect in an area it has already filed cards for in the same pass (or recently), there is no affordance to extend an existing umbrella card — every finding becomes a new card with full create-card → claim → implement → attest → done → commit ceremony. A recent batch filed 19 separate `yaml-lite`/frontmatter-emitter cards in ~24h, all of which were variations on one theme (round-trip integrity of the hand-rolled YAML subset). Per the stored `umbrella cards during iterative debugging` preference, that should have been one growing umbrella card with a DoD list that extended as new findings landed. This card scopes the missing affordance: a CLI verb to append a finding to an open card's DoD, plus the audit-deck workflow change that uses it."
status: open
stage: null
contribution: medium
created: "2026-05-28T04:01:37Z"
closed_at: null
human_gate: session
advances: []
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] PROCESS: trigger condition decided (see Decision required, item 1) and recorded in `## Decision` body section.
  - [ ] PROCESS: append mechanism decided (see Decision required, item 2) and recorded in `## Decision` body section.
  - [ ] PROCESS: closure semantics decided (see Decision required, item 3) and recorded in `## Decision` body section.
  - [ ] MECHANICAL: `goc append-dod <umbrella-slug> "<finding>"` (or chosen verb name) implemented in the engine. The new DoD line is inserted before the existing `PROCESS:` / `EMPIRICAL:` tail items where possible; original ordering is preserved otherwise. Refuses if the target card is not `open` or `active`.
  - [ ] MECHANICAL: `audit-deck` SKILL.md updated to detect "an open card whose summary/tags/area match this finding" before filing fresh, and to call the append verb instead when matched. The matching heuristic is documented in the skill body.
  - [ ] EMPIRICAL: simulated re-run on the recent 19-card yaml-lite batch (or an equivalent fixture) shows N-1 cards collapsed into one umbrella DoD with N items; ceremony cost (file + claim + close per finding) reduced to a single cycle.
  - [ ] PROCESS: only `goc/` and `goc/templates/` are hand-edited; `python scripts/sync_plugin_assets.py --check` passes.
  - [ ] PROCESS: `uv run goc validate` passes.
---

# audit-deck-cannot-extend-an-existing-umbrella-card-for-related-findings

## What's missing

`audit-deck` files a new card per finding. There is no affordance to extend an existing umbrella card's DoD list when a finding is a sibling of one already filed. The result, observed in a recent autonomous batch: 19 separate cards filed in ~24h for variations on a single theme (`yaml-lite` / frontmatter-emitter round-trip integrity), each paying the full create-card → claim → implement → attest → done → commit ceremony cost.

Per the stored team preference (`feedback_umbrella_cards`): "one growing card per multi-failure-mode problem; split only when Rodja asks." The batch violated that preference because the methodology gave audit-deck no way to honor it — the only filing primitive is `goc new`, which always creates a fresh card.

## Why human_gate=session

Three open design choices need a human pick before implementation; each has credible alternatives. See `## Decision required` below.

## Decision required

### 1. Trigger condition — when does audit-deck *extend* vs. file fresh?

Options:

- **Manual.** Audit-deck always files fresh; humans (or a separate hygiene pass) periodically consolidate sibling cards. Status quo + an after-the-fact merge tool.
- **Tag-driven.** When a finding's primary tag (`yaml-lite`, `frontmatter-emitter`, etc.) matches an open card with the same tag, extend that card. Requires either canonical area tags or a derived "subject" from the title.
- **Same-file heuristic.** When the finding's cited file path overlaps with an open card's cited file path (`goc/engine.py` regions), extend.
- **Explicit umbrella tag.** A card tagged `umbrella: yaml-lite-roundtrip` is the auto-target for any new finding tagged `yaml-lite-roundtrip`. The umbrella is opt-in; first finding files fresh, subsequent ones append.

The fourth option scales best (explicit intent, no false matches), at the cost of requiring the first finding's author to mark the umbrella.

### 2. Append mechanism — engine verb vs. body edit

Options:

- **`goc append-dod <slug> "<text>"`** — engine verb that mutates the frontmatter `definition_of_done` block, preserving format and ordering invariants. Auto-commits per workflow.auto_commit.
- **Direct file write** — the skill writes to the README and reformats. Simpler, but loses the schema-aware safety the engine provides for other frontmatter mutations.

### 3. Closure semantics — when does an umbrella close?

Options:

- **All-DoD-ticked.** Standard: every appended item must be ticked. Works for finite umbrellas (a known set of issues to find), risky for open-ended ones (the umbrella may never close as new findings land).
- **Time-boxed.** Umbrella closes when its DoD has been stable (no new appends) for N days, even if some items are unticked-but-explicitly-deferred. Requires a `deferred: <reason>` marker on individual items.
- **Manual mark-finite.** A `--finalize` verb freezes the DoD; further appends are rejected. Closer pattern to current cards; relies on the closer to make the call.

## Why it matters

The cost: across the 19-card batch, the per-card ceremony multiplier (skill loads ~680 lines, attest, commit) was paid 19 times for what was conceptually one theme. A single umbrella card with 19 DoD items would have paid that cost once — roughly a 95% reduction in ceremony tokens on that theme alone, with no loss in fix quality (each item still gets its own reproducer in the card directory if useful, just no separate frontmatter / log.md / attest cycle).

The benefit is concentrated in the autonomous-agent regime where `audit-deck` is the work generator; the deliberate, human-paced regime rarely fires audit-deck repeatedly on the same module within a single window.

## Cross-references

- `trim-token-cost-of-autonomous-card-cycles` — sibling umbrella covering the mechanical gate:none token-cost wins.
- `heaviest-skills-re-load-full-methodology-briefing-per-card-cycle` — sibling session-gated card on the orthogonal axis (skill body size, not card count).
- The recent yaml-lite/emitter cluster of 19 closed cards is the motivating evidence.

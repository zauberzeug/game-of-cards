---
title: audit-deck-cannot-extend-an-existing-umbrella-card-for-related-findings
summary: "When `audit-deck` finds a defect in an area it has already filed cards for in the same pass (or recently), there is no affordance to extend an existing umbrella card — every finding becomes a new card with full create-card → claim → implement → attest → done → commit ceremony. A recent batch filed 19 separate `yaml-lite`/frontmatter-emitter cards in ~24h, all of which were variations on one theme (round-trip integrity of the hand-rolled YAML subset). Per the stored `umbrella cards during iterative debugging` preference, that should have been one growing umbrella card with a DoD list that extended as new findings landed. This card scopes the missing affordance: a CLI verb to append a finding to an open card's DoD, plus the audit-deck workflow change that uses it."
status: open
stage: null
contribution: medium
created: "2026-05-28T04:01:37Z"
closed_at: null
human_gate: none
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

## Decision

*Resolved 2026-10-22T05:27:51Z:* Trigger: Explicit umbrella tag. Append: goc append-dod <slug> "<text>". Closure: All-DoD-ticked.

*Reasoning:* The maintainer answered the three design questions in a human session on 2026-10-22: an opt-in umbrella marker gives explicit intent without false matches, the engine verb keeps DoD appends schema-safe like the other frontmatter writers, and an umbrella closes like every other card once each appended item is ticked, accepting the open-ended-umbrella risk the card notes

## Why it matters

The cost: across the 19-card batch, the per-card ceremony multiplier (skill loads ~680 lines, attest, commit) was paid 19 times for what was conceptually one theme. A single umbrella card with 19 DoD items would have paid that cost once — roughly a 95% reduction in ceremony tokens on that theme alone, with no loss in fix quality (each item still gets its own reproducer in the card directory if useful, just no separate frontmatter / log.md / attest cycle).

The benefit is concentrated in the autonomous-agent regime where `audit-deck` is the work generator; the deliberate, human-paced regime rarely fires audit-deck repeatedly on the same module within a single window.

## Cross-references

- `trim-token-cost-of-autonomous-card-cycles` — sibling umbrella covering the mechanical gate:none token-cost wins.
- `heaviest-skills-re-load-full-methodology-briefing-per-card-cycle` — sibling session-gated card on the orthogonal axis (skill body size, not card count).
- The recent yaml-lite/emitter cluster of 19 closed cards is the motivating evidence.

---
title: refine-deck-drops-structural-findings-by-defaulting-to-propose-not-file
summary: "refine-deck's `propose, don't apply` framing applies to every finding class, so when project hooks extend the skill with a structural pattern-discovery pass the framing causes agents to surface findings to chat/scratch and skip filing. The asymmetry with audit-deck's mandatory Phase 3 `Park-or-disprove` disposition rule means refine-deck rounds can surface N structural candidates and file 0 cards while passing the skill's own success criteria. Decision needed: full-mirror of audit-deck's bound, minimal Step 4.5 audit, or per-category disposition rules."
status: done
stage: null
contribution: high
created: "2026-05-23T04:02:33Z"
closed_at: "2026-05-23T05:23:48Z"
human_gate: none
advances: []
advanced_by:
  - refine-deck-skill-missing-consuming-repo-hook-override
tags: [bug]
definition_of_done: |
  - [x] `goc/templates/skills/refine-deck/SKILL.md` updated per the chosen option (see `## Decision required`).
  - [x] `scripts/sync_plugin_assets.py` regenerates the mirror copies (`.claude/skills/`, `.codex/skills/`, `claude-plugin/skills/`, `codex-plugin/skills/`) without drift.
  - [x] `python scripts/sync_plugin_assets.py --check` passes (CI tripwire).
  - [x] An autonomous refine-deck round on this repo's own deck produces ≥1 filing or explicit disposition (filed / disproved / unverified-parked) for every surfaced non-hygiene candidate — verifies the discipline change took.
  - [x] Hygiene-category behaviour (mechanical edits to stale parks, missing summaries, defunct cites, predicate-failing tags) is unchanged — verified by re-running the hygiene categories and confirming the apply-direct path still fires.
  - [x] If the chosen option introduces per-category disposition rules, the new taxonomy is reflected in `AGENTS.md` or a sibling note so future readers see the contract.
worker: {who: "claude[bot]", where: main}
---

# refine-deck-drops-structural-findings-by-defaulting-to-propose-not-file

## Location

`goc/templates/skills/refine-deck/SKILL.md`, specifically:

- Line 36 — top-of-body framing: `Surface rot and propose corrective edits — never apply them silently.`
- Lines 57-59 — Step 1 disposition rule: `Each surfaced issue gets a one-line recommendation; the user or autonomous loop decides whether to flip to Skill(advance-card), Skill(create-card) (for a SCHEMA.md PR), or move on.`
- Lines 246-254 — Step 3 (new canonical tags) restates `propose, don't apply` for tag predicates. This restatement is legitimate for SCHEMA.md PRs but the framing tone leaks across all finding classes.

Compare against `goc/templates/skills/audit-deck/SKILL.md` lines 168-189 — Phase 3 "Park-or-disprove unfollowed candidates (mandatory)" with an explicit "maximum-amnesia bound" at line 189. `refine-deck` has no equivalent phase or named bound.

## What's broken

The skill body steers agents toward "surface, then stop" for any finding class that doesn't have an implicit mechanical-apply path.

The hygiene categories (stale `unverified` parks, defunct file:line cites, missing summaries, predicate-failing tags, orphaned-edge sub-checks) work fine — those categories already steer the agent toward direct mechanical edits to frontmatter / file paths. The bug bites when project hooks extend `refine-deck` with a **structural pattern-discovery pass** — which the skill body explicitly authorizes at lines 25-34:

```
The consuming repo may extend this hygiene flow via
`.game-of-cards/hooks/refine-deck.md` (already loaded above) — e.g.,
to demand a pattern-discovery pass with specialized reviewers, ...
declare which artifacts ... are in-scope for framework-tier findings
```

Once a project uses that authorization, the reviewer agents produce structural candidates (epic-shaped clusters, meta-decision umbrellas, missing canonical-reference families, contribution-recall proposals) for which the skill body provides no implicit-apply path AND no explicit filing rule. The "propose, don't apply" framing at line 36 is read first; the hook's authorization is read after; the agent has already locked in the proposal disposition by the time it gets to Step 4, and Step 4 ("surface and recommend") terminates the skill without a disposition audit.

The asymmetry with `audit-deck` is structural:

| Skill | Filing default | Pre-commit audit | Maximum-amnesia bound |
|---|---|---|---|
| `audit-deck` | File every confirmed defect | Phase 3 "Park-or-disprove unfollowed candidates (mandatory)" | Explicit (Phase 3, line 189) |
| `refine-deck` | Propose; user decides | None (Step 4 terminates the skill) | None |

The candidate-surface budget is similar — both skills steer toward ≥3 reviewer agents producing ≥3 candidates each — so the volume mismatch in dropped findings tracks the disposition-rule mismatch.

## Empirical evidence (downstream reproduction)

A downstream consuming repo that extended `refine-deck` with a project-local hook authorising a structural pattern-discovery pass (per lines 25-34) reports two same-day rounds with 6 + 5 reviewer agents on `model: opus`. Findings across the two rounds:

- 1 near-certainty meta-decision card (≥3 reviewers converged)
- 1 strong epic candidate
- 4 canonical-tag predicate candidates
- 6 epic / topic-stub candidates
- 13 contribution-recall proposals
- 8 same-paper polarity conflicts
- 7 missing schema edges
- 3 absent canonical-reference families (round 2)
- 6 additional structural cards (round 2)

Commits landed: validator-error closures and missing-edge wires only. **Cards filed for the 12 structural findings: 0.** All structural findings sat in the project's gitignored scratch directory, which the project's own docs describe as "may be deleted by other agents or session resets at any time."

For contrast, the same project's earlier `refine-deck` runs (before the local hook added the structural pattern-discovery pass) DID file structural cards. A project-local override said *"Refine-deck IS allowed to file cards when the finding is structural, not a defect."* That passive carve-out lost to the upstream skill's framing tone in the structural-pass scenario — agents read the upstream body first, locked in the proposal stance, treated the carve-out as optional.

There is no `reproduce.py` for this card because the failure mode is skill-body discipline, not executable code. The reproduction is the downstream evidence above; the verification is reading the cited line ranges and comparing against `audit-deck`'s Phase 3.

## Why it matters

Token cost: a `refine-deck` round with structural pattern discovery produces O(10s) of high-value research candidates from O(5) `opus` reviewers. Dropping these on the floor wastes the round's full research budget. A round that surfaces N findings and files 0 cards has discarded N findings' worth of tokens.

UX cost: two adjacent hygiene skills (`audit-deck`, `refine-deck`) currently have opposite default dispositions for surfaced candidates. Agents reading both skills in the same project will infer two different operating models for what to do with a surfaced finding, which is the kind of inconsistency `audit-deck` itself is designed to hunt.

Discipline drift: the predecessor card [refine-deck-skill-missing-consuming-repo-hook-override](../refine-deck-skill-missing-consuming-repo-hook-override/) landed the hook-extension point. The discipline (what consuming repos should do with the findings their extended hook surfaces) didn't catch up. This card closes that gap.

## Decision

*Resolved 2026-05-23T04:49:36Z:* Apply Option A — full mirror of audit-deck Phase 3 discipline (rewrite framing as filing-authorisation + add Step 4.5 pre-commit disposition audit + rewrite Step 2/3 recommendations as imperative for cards)

*Reasoning:* Maximum symmetry with audit-deck's mature Park-or-disprove discipline preferred over the per-category-rules recommendation; chosen by user
## Notes on fix scope

This card patches the upstream skill body. The skill ships from `goc/templates/skills/refine-deck/SKILL.md` and is mirrored to `.claude/skills/`, `.codex/skills/`, `claude-plugin/skills/`, `codex-plugin/skills/` by `scripts/sync_plugin_assets.py` (pre-commit). The fix lands as a single source-of-truth edit; the sync hook handles the four mirror copies.

The fix is **additive** for projects already filing per the carve-out pattern — they continue working with no change. It is **corrective** for projects relying on the current "propose, don't apply" default: they'll start filing what they used to drop, which is the intended behaviour change.

No CLI changes. No schema changes. No new canonical tags. `SKILL.md` edits only.

## Cross-references

- Predecessor: [refine-deck-skill-missing-consuming-repo-hook-override](../refine-deck-skill-missing-consuming-repo-hook-override/) — landed the hook-extension point that downstream projects use for the structural pattern-discovery pass. Closed 2026-05-14.
- Discipline model: `goc/templates/skills/audit-deck/SKILL.md` Phase 3 (lines 168-189) — "Park-or-disprove unfollowed candidates (mandatory)" is the symmetry target.
- Related closed card: [refine-deck-fails-to-load-on-the-rot-it-is-meant-to-clean-up](../refine-deck-fails-to-load-on-the-rot-it-is-meant-to-clean-up/) — different defect (skill failed to load when validator errors existed); not a root-cause overlap, but in the same skill body.

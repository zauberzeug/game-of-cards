---
title: tag-dod-items-by-method-class-test-experiment-edit-or-decision
summary: "Definition-of-Done checkboxes today flatten four epistemically distinct closure contracts — provable assertions, experimental outcomes, inspection-verifiable edits, and pure agreements — into uniform ticked-or-not. The most consequential conflation is empirical items: a `- [ ]` line that reads as a must-pass gate when the correct semantics is must-run-and-record-the-verdict. Proposes a one-token method-tag prefix per DoD line plus a warning-only validator check for migration safety."
status: open
stage: null
contribution: medium
created: "2026-05-23T05:07:26Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [documentation, infra]
definition_of_done: |
  - [ ] decision recorded in `## Decision` section: which tag format (`[TDD]` bracket prefix vs `TDD:` colon prefix); whether taxonomy is four-class or includes `[SPIKE]`; validator regex scope (line-anchored vs lenient)
  - [ ] `goc/templates/skills/card-schema/SKILL.md` extended with a new `### DoD method tags` subsection nested inside the existing `## Definition of Done` section, defining the chosen vocabulary and the discipline rule ("prefer TDD whenever a closed-form expected value exists")
  - [ ] `goc/templates/skills/create-card/SKILL.md` Step 5 example DoD updated to demonstrate the chosen tagging convention end-to-end
  - [ ] `goc/engine.py` validator emits a fourth warning class (`UNTAGGED_DOD_ITEM`) for DoD checkboxes lacking a method tag — warning-only, sibling to STALE_BLOCKED / ORPHAN_BLOCKED / CASCADE_CHAIN_ROOT in `compute_blocker_warnings`
  - [ ] pre-commit `sync-plugin-assets` propagates the SKILL.md edits to all five consumer surfaces (claude-plugin, codex-plugin, openclaw-plugin, .claude/, .codex/) without drift; CI tripwire passes
---

# Tag DoD items by method class (test / experiment / edit / decision)

## What's missing

The `definition_of_done` field has one closure semantic: `- [x]` means "this criterion is satisfied; the card is one box closer to closure." That semantic is **correct for three out of four common DoD-item shapes** but **wrong for one** — the experimental-outcome shape, where the right closure rule is "the experiment ran and the verdict was recorded; the verdict's direction does not gate closure."

Four shapes show up in the wild:

1. **Provable assertion (TDD-class)** — deterministic predicate with a closed-form expected value. Example: `- [ ] reproduce.py exits zero (defect no longer fires)`. Closure: assertion holds.
2. **Experimental outcome (EMPIRICAL-class)** — sweep, A/B, statistical test with a pre-registered falsifier. Example: `- [ ] paired Wilcoxon on the optimization metric across N seeds gives p < 0.05 for arm A > arm B`. Closure: **the experiment ran and the verdict (whichever way) is documented** — not that p was below the threshold.
3. **Inspection-verifiable edit (MECHANICAL-class)** — code or doc edit a reviewer can confirm by reading. Example: `- [ ] schema.yaml gains the new tag entry`. Closure: edit landed.
4. **Decision / cross-reference (PROCESS-class)** — agreement, gate flip, parent's `advanced_by` updated. Example: `- [ ] decision recorded in ## Decision section`. Closure: the recording happened.

Today these four are visually indistinguishable. When the deck contains EMPIRICAL items framed as TDD-style assertions, two failure modes emerge:

- A run-and-recorded experiment with a null result reads as "incomplete work" and the box stays unchecked, even though the closure contract is satisfied. The next reader sees a still-open DoD and re-runs the experiment, wasting time on already-decided questions.
- A pre-registered falsifier that fires (the experiment ran and showed the predicted effect was absent) gets retroactively edited to look like a TDD failure, masking the experimental nature of the original claim.

The four-class vocabulary makes each item's closure semantic legible without prose.

## Why the proposal lands upstream

Consuming repos have codified this discipline locally in their own contributor docs; the underlying epistemology is project-agnostic and ports cleanly to any GoC-using codebase that has a mix of test-class, sweep-class, edit-class, and decision-class DoD items. Lifting it to `card-schema` lets downstream repos drop their local codifications and gives the validator a hook to surface untagged items.

The proposed surface is minimal: a one-token prefix on each DoD line, a `card-schema` SKILL.md subsection documenting the vocabulary, and a warning-only validator check (no breakage for legacy cards).

## Decision required

### Reasoning

Three coupled sub-decisions need a single human pick before mechanical implementation is safe:

1. **Tag format on the DoD line.** Bracketed prefix `[TDD] ` is parseable and visually distinct but introduces a second pair of square brackets adjacent to the existing checkbox brackets (`- [ ] [TDD] ...`), which can hurt readability and confuse the line-anchored regex. Colon-suffix prefix `TDD: ` reads more naturally and avoids the bracket-collision, but is slightly less greppable.
2. **Taxonomy size.** The proposal names four classes. XP-style **SPIKE** items (exploratory work whose "done" is "I understand X enough to file the next card") arguably belong as a fifth class — they share MECHANICAL's inspection-verifiable closure but have a fundamentally different cognitive shape (exploration with no falsifier vs edit with a known target). Folding SPIKE into MECHANICAL loses the distinction; promoting it adds vocabulary surface.
3. **Validator scope.** Strict line-anchored regex `^- \[[ x]\] \[(TDD|...)\] ` makes the discipline mechanically enforceable but rejects future format variants. Lenient any-position match is more flexible but admits drift.

Without a human go/no-go on these three, mechanical implementation could land a format that needs reworking across every existing card the moment it ships.

### Option A — Four classes, `[TDD]` bracket prefix, line-anchored validator

Adopt the proposal as drafted.

**Pros:**
- Minimal surface (one SKILL.md section, ~40 LOC validator change).
- Bracket prefix is greppable: `grep '^- \[[ x]\] \[EMPIRICAL\]' deck/*/README.md` enumerates every empirical DoD item.
- Line-anchored regex matches the existing DoD-detection predicate (`^- \[[ x]\]` at `engine.py:493`), keeping parser conventions uniform.

**Cons:**
- Double-brackets at line start (`- [ ] [TDD] ...`) is visually noisy.
- Four classes may under-serve exploratory SPIKE-shape work, forcing such items to wear `[MECHANICAL]` against semantics.

**File:line preview:**
- `goc/templates/skills/card-schema/SKILL.md:328` — insert new `### DoD method tags` subsection between `### Layer-1 format` (ends line 327) and `## Relationship fields` (starts line 329).
- `goc/templates/skills/create-card/SKILL.md:194` — update the example DoD block to use the four bracketed prefixes.
- `goc/engine.py:1119` — extend `compute_blocker_warnings` with a fourth `BlockerWarning` class that scans each card's parsed DoD lines and emits `UNTAGGED_DOD_ITEM` for any `- [ ]`/`- [x]` not matching `\[(TDD|EMPIRICAL|MECHANICAL|PROCESS)\]`.

### Option B — Four classes, `TDD:` colon-suffix prefix, line-anchored validator

Same vocabulary and validator scope as Option A; tag rendered as `TDD: ` at the start of each DoD criterion: `- [ ] TDD: reproduce.py exits zero`.

**Pros:**
- Cleaner visual: no bracket-on-bracket collision.
- Reads as natural-language: "TDD: the assertion holds" mirrors spoken framing.
- Regex stays simple: `^- \[[ x]\] (TDD|EMPIRICAL|MECHANICAL|PROCESS): `.

**Cons:**
- Slightly less greppable than brackets (colon is a common character).
- Breaks symmetry if the deck later adopts other `[bracket]` metadata conventions.

**File:line preview:** Same surfaces as Option A; only the rendered tag format differs.

### Option C — Reject the proposal

Leave the DoD as-is. Document the empirical-vs-assertion distinction informally in body prose of cards that mix the two, rather than in the schema.

**Pros:**
- Zero migration cost forever; no validator surface to maintain.
- Preserves the principle that DoD is a free-text contract — formatting discipline lives in author convention, not schema enforcement.
- Avoids the future-fork risk of having to extend the taxonomy (SPIKE, SECURITY, PERF, …) once the four classes are baked in.

**Cons:**
- Loses the most consequential discipline-clarification: empirical items continue to read as must-pass assertions, perpetuating the false-incompletion failure mode.
- Downstream repos keep maintaining duplicate prose; the next consuming repo re-derives the discipline from scratch.
- The validator-warning surface is exactly the kind of low-stakes mechanical reminder GoC is well-suited to ship (cf. `STALE_BLOCKED`).

**File:line preview:** No code change; doc-only revision to `card-schema` SKILL.md noting the four-class informal discipline as guidance without enforcement.

### Recommendation

**Option B (four classes, colon-suffix `TDD:` prefix)**, with the SPIKE sub-question deferred to a follow-up card filed once the four-class shape has been lived with for ~10 new cards. Dominant pro: the colon-suffix avoids the double-bracket visual noise without losing greppability, and the four-class baseline is a strictly-smaller-and-safer adoption surface than the five-class variant. Validator scope: line-anchored, matching the existing DoD-detection predicate.

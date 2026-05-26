---
title: tag-dod-items-by-method-class-test-experiment-edit-or-decision
summary: "Definition-of-Done checkboxes today flatten four epistemically distinct closure contracts — provable assertions, experimental outcomes, inspection-verifiable edits, and pure agreements — into uniform ticked-or-not. The most consequential conflation is empirical items: a `- [ ]` line that reads as a must-pass gate when the correct semantics is must-run-and-record-the-verdict. Proposes a one-token method-tag prefix per DoD line plus a warning-only validator check for migration safety."
status: done
stage: null
contribution: medium
created: "2026-05-23T05:07:26Z"
closed_at: 2026-05-26T20:11:13Z
human_gate: none
advances: []
advanced_by: []
tags: [documentation, infra]
definition_of_done: |
  - [x] PROCESS: decision recorded in `## Decision` section: which tag format (`[TDD]` bracket prefix vs `TDD:` colon prefix); whether taxonomy is four-class or includes `[SPIKE]`; validator regex scope (line-anchored vs lenient)
  - [x] MECHANICAL: `goc/templates/skills/card-schema/SKILL.md` extended with a new `### DoD method tags` subsection nested inside the existing `## Definition of Done` section, defining the chosen vocabulary and the discipline rule ("prefer TDD whenever a closed-form expected value exists")
  - [x] MECHANICAL: `goc/templates/skills/create-card/SKILL.md` Step 5 example DoD updated to demonstrate the chosen tagging convention end-to-end
  - [x] MECHANICAL: `goc/engine.py` validator emits a fourth warning class (`UNTAGGED_DOD_ITEM`) for DoD checkboxes lacking a method tag — warning-only, sibling to STALE_BLOCKED / ORPHAN_BLOCKED / CASCADE_CHAIN_ROOT in `compute_blocker_warnings`
  - [x] TDD: pre-commit `sync-plugin-assets` propagates the SKILL.md edits to all five consumer surfaces (claude-plugin, codex-plugin, openclaw-plugin, .claude/, .codex/) without drift; CI tripwire passes
worker: {who: "claude[bot]", where: main}
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

## Decision

*Resolved 2026-05-26T12:10:35Z:* Option B — four method classes (TDD / EMPIRICAL / MECHANICAL / PROCESS) with a colon-suffix prefix on each DoD line (e.g. TDD: ...), plus a line-anchored validator emitting a warning-only UNTAGGED_DOD_ITEM. The SPIKE fifth class is deferred to a follow-up card filed once the four-class shape has been lived with for about 10 new cards.

*Reasoning:* The colon-suffix avoids the double-bracket visual noise next to the checkbox without losing greppability, and the four-class baseline is a strictly-smaller-and-safer adoption surface than the five-class variant. Line-anchored validator scope matches the existing DoD-detection predicate.

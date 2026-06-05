---
title: dod-fence-mask-reimplements-commonmark-fences-and-keeps-drifting
status: open
stage: null
contribution: medium
created: "2026-06-05T04:54:13Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, meta-fix, api-contract]
definition_of_done: |
  - [ ] (replace with real criteria after the decision)
---

# The DoD fence mask is a hand-rolled CommonMark fence parser that keeps drifting

`_dod_fenced_mask` in `goc/engine.py` masks fenced-code lines so an
illustrative `- [ ]` inside a code block in a card's `definition_of_done`
isn't counted as a real DoD item. It is a hand-rolled partial reimplementation
of CommonMark §4.5 (fenced code blocks), and it has now been patched **three
separate times**, each time for a different spec rule discovered only after a
card hit the bug:

| Card | Rule that was missing |
|---|---|
| [dod-checkbox-inside-fenced-code-block-counts-as-real-item-and-blocks-closure](../dod-checkbox-inside-fenced-code-block-counts-as-real-item-and-blocks-closure/) | masking fenced lines at all |
| [dod-scanners-treat-a-tilde-fence-as-closing-a-backtick-code-block](../dod-scanners-treat-a-tilde-fence-as-closing-a-backtick-code-block/) | close requires the *same* fence char and run length ≥ opener |
| [dod-scanners-treat-an-info-string-fence-line-as-closing-a-code-block](../dod-scanners-treat-an-info-string-fence-line-as-closing-a-code-block/) | close may not carry an info string |

This is the same shape the repo has already named elsewhere
([yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting](../yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting/)):
a hand-rolled scanner that re-derives a spec one bug-report at a time, with no
single authority for "what does conforming look like." Each fix is correct in
isolation, but the next gap is only found when a card author trips it — and
the cost lands on a card that becomes silently impossible to close.

## Suspected remaining gaps (unverified — to be confirmed by the chosen work)

CommonMark §4.5 rules `_dod_fenced_mask` does **not** currently implement, any
of which could mis-mask a real-world DoD:

- **Indentation of the opening fence** — a fence may be indented up to 3
  spaces; the run regex tolerates leading whitespace but does not strip the
  matching indent from the closing fence comparison, nor reject a 4-space
  "fence" (which is an indented code block, not a fenced block).
- **Closing-fence indentation** — a closing fence may be indented 0–3 spaces
  independently of the opener.
- **Indented code blocks (4-space)** — never masked at all; a `- [ ]` inside a
  4-space-indented example would be counted as a real item.
- **Backtick info strings containing backticks** — per spec a backtick opening
  fence's info string may not contain a backtick; the current opener is lax
  (conservative — masks more, so likely harmless, but worth confirming).

These are *suspected* and must be reproduced before any are treated as defects.

## Decision required

Three credible directions; a human (or the project rubric) should pick before
implementation:

1. **Holistic conformance pass (audit + close all real gaps now).** Enumerate
   the §4.5 rules, write a reproduce case per gap, fix every confirmed one in
   `_dod_fenced_mask`, and add a conformance test matrix. Pro: stops the
   drip. Con: spends effort on gaps no real card has hit yet (DoDs are short,
   author-written markdown — indented code blocks and indentation tricks are
   rare in practice).

2. **Adopt a real CommonMark parser** (e.g. vendor a tiny fence tokenizer, or
   depend on `markdown-it-py` / `commonmark`) and delete the hand-rolled scan.
   Pro: spec-correct by construction, no future drift. Con: a new dependency
   (or vendored code) for a deliberately-small package; the mask only needs
   fence *boundaries*, not a full parser.

3. **Status quo — keep patching per-discovered-case, close this as won't-fix.**
   Accept that DoD fence handling is a long-tail and that the three fixes so
   far cover the realistic cases. Pro: no speculative work. Con: the 4th gap
   lands on a future card as a silent can't-close.

Recommendation leans toward **(1) scoped to the gaps a `reproduce.py` actually
confirms** — file/fix only the real ones, skip the purely theoretical — which
is the audit-deck "meta-fix at the Nth instance" pattern. But the dependency
question (2) is a genuine project-taste call, hence the gate.

## Why it matters

The DoD checkbox set is the machine-checkable closure contract. A mis-mask in
either direction is a correctness bug: under-mask and a real item is hidden
(`goc done` closes a card with unfinished work); over-mask and an illustrative
example blocks closure forever. The mask routes all three DoD scanners
(`count_dod_boxes`, `_dod_box_indices`, `untagged_dod_items`), so a single
fence-parsing gap affects closure gating, the quality-pass rewriter's index
space, and untagged-item detection simultaneously.

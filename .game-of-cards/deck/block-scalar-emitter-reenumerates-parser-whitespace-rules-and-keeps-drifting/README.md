---
title: block-scalar-emitter-reenumerates-parser-whitespace-rules-and-keeps-drifting
summary: "The block-scalar emitter (`_emit_block_field`, engine.py:287) and the vendored block-scalar parser (`_parse_block_scalar`, _vendor/yaml_lite.py) hand-maintain mirror-image rules for which lines carry meaningful whitespace and how the block indent is fixed. Because each side restates the other's whitespace handling rather than sharing one contract, the two keep drifting — 5 separate bug cards have now patched this one family one whitespace edge case at a time (leading, interior, trailing, less-indented, leading-only). Decision-gated on how to make the emit->parse round-trip whitespace-faithful by construction."
status: open
stage: null
contribution: medium
created: "2026-06-24T19:45:11Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - block-scalar-parser-chops-characters-when-a-later-line-is-less-indented-than-the-first
  - block-scalar-parser-collapses-whitespace-only-content-lines
  - block-scalar-parser-strips-trailing-whitespace-breaking-emit-parse-round-trip
  - frontmatter-emitter-mangles-block-scalar-values-that-carry-leading-whitespace
  - frontmatter-emitter-drops-leading-whitespace-only-line-in-block-scalar-values
tags: [meta-fix, infra, api-contract]
definition_of_done: |
  - [ ] PROCESS: pick a factoring (see `## Decision required`) and record it in log.md with rationale.
  - [ ] MECHANICAL: the emitter's block-indent / indicator decision and the parser's whitespace handling share one contract (one source of truth), instead of two independent hand-maintained restatements that can disagree on a whitespace shape.
  - [ ] TDD: every existing block-scalar round-trip regression test in the family below still passes unchanged (that family is the contract the unified mechanism must preserve).
  - [ ] TDD: a single property-style test asserts the round-trip invariant directly — for a representative corpus of multi-line strings with arbitrary leading / interior / trailing / mixed whitespace, `parse(emit(s)) == s` — so a future emitter or parser change that reinterprets a new whitespace shape is caught by construction rather than by a fresh per-shape bug.
  - [ ] PROCESS: `uv run goc validate` clean; `python scripts/sync_plugin_assets.py --check` green (vendored parser/emitter mirrored into plugin payloads).
---

# Block-scalar emitter re-enumerates parser whitespace rules and keeps drifting

## Summary

The frontmatter block-scalar emitter (`_emit_block_field` in
`goc/engine.py`) and the vendored block-scalar parser (`_parse_block_scalar`
in `goc/_vendor/yaml_lite.py`) each hand-maintain their own model of how
whitespace in a multi-line value is rendered and recovered: which lines are
"structural blanks" vs whitespace-carrying content, how the block indent is
fixed (inferred from the first content line vs pinned by an explicit `|2`
indicator), and what counts as meaningful trailing/leading whitespace.
Because the emitter's knowledge is a *copy* of the parser's rather than
*derived* from it, the two keep drifting: every time one side is hardened or
a new whitespace shape is noticed, a fresh per-shape round-trip bug lands.
**Five separate bug cards have now patched this one family one whitespace
edge case at a time.** That is the missing-abstraction signal.

This is the block-scalar sibling of the inline-scalar root card
[frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting](../frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting/),
which captures the same drift shape for `_yaml_inline`'s quote trigger. The
two roots are distinct code sites (block-scalar indent/indicator handling vs
inline quoting) but the same architectural defect: emitter restates parser
behaviour by hand.

## What's broken (the recurring shape)

The emitter decides the block indent / indicator with hand-maintained
conditions at `goc/engine.py:287` (`_emit_block_field`), e.g. "emit an
explicit `|2` indicator when the value's leading whitespace would otherwise
be lost." The parser independently decides, at `goc/_vendor/yaml_lite.py`
(`_parse_block_scalar`), when a line is a structural blank (`block_indent is
None` short-circuit), how the block indent is fixed, and which trailing
whitespace is chomped. When the two restatements disagree about a particular
whitespace shape, the emitter writes content the parser then reinterprets —
silent data loss on the emit->parse round-trip (or, for the over-indented
case, a hard raise).

## The family (record axis — instances of this one shape)

Each instance fixed one whitespace shape; the unified mechanism must preserve
all of them:

- [block-scalar-parser-chops-characters-when-a-later-line-is-less-indented-than-the-first](../block-scalar-parser-chops-characters-when-a-later-line-is-less-indented-than-the-first/)
  — a later content line less-indented than the first.
- [block-scalar-parser-strips-trailing-whitespace-breaking-emit-parse-round-trip](../block-scalar-parser-strips-trailing-whitespace-breaking-emit-parse-round-trip/)
  — trailing whitespace on a content line.
- [block-scalar-parser-collapses-whitespace-only-content-lines](../block-scalar-parser-collapses-whitespace-only-content-lines/)
  — interior whitespace-only lines.
- [frontmatter-emitter-mangles-block-scalar-values-that-carry-leading-whitespace](../frontmatter-emitter-mangles-block-scalar-values-that-carry-leading-whitespace/)
  — first non-blank content line begins with whitespace.
- [frontmatter-emitter-drops-leading-whitespace-only-line-in-block-scalar-values](../frontmatter-emitter-drops-leading-whitespace-only-line-in-block-scalar-values/)
  — a leading whitespace-only line before the first non-blank line.

## Why it matters

`emit_frontmatter` routes every multi-line string field (`summary`,
`definition_of_done`, any multi-line value) through `_emit_block_field`, and
every read-then-re-emit verb (`goc decide`, `goc quality-pass`, `goc
migrate-list-style`, `goc new`) rewrites the whole frontmatter through it.
Each new whitespace shape that drifts is a silent corruption of authored card
content on the next mutation — the exact failure the frontmatter family is
supposed to guarantee against. The per-shape fixes are correct but reactive;
the family will keep producing instances until the emitter's block-indent
decision and the parser's whitespace handling share one contract.

## Decision required

How to converge the emitter and parser onto one whitespace contract. Credible
options:

1. **Always emit the explicit indent indicator (`|2`/`|2-`).** Pin the block
   indent unconditionally so the parser never infers it; the emitter no longer
   reasons about whether leading whitespace "would be lost." Simplest, but
   changes the wire format of every multi-line field (large mechanical churn
   across the deck) and re-flows existing cards on next touch.
2. **Derive the emitter's indicator decision from a parser-exported predicate.**
   Expose, from `yaml_lite`, the single function that answers "does this value
   need an explicit indent indicator to round-trip?" and have the emitter call
   it — one source of truth, minimal wire-format change. Mirrors the factoring
   the inline-quote root card proposes for `_yaml_inline`.
3. **Property-test-only freeze.** Keep both sides as-is but add the
   `parse(emit(s)) == s` property test over a whitespace corpus (DoD item 4)
   as the contract, accepting that new shapes are caught at test time rather
   than prevented by construction. Cheapest; does not remove the duplication.

The property-style round-trip test (DoD item 4) is valuable under any option
and should land regardless of the factoring chosen. See the inline-quote root
card's `## Decision required` for the parallel discussion on `_yaml_inline`.

## Note

This card closes when the *factoring is decided and applied* — it is an
architectural meta-fix, not a per-shape bug. The five instances above are
already fixed individually (record-axis `advanced_by` edges); this card
prevents the sixth.

---
title: yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting
summary: "`_vendor/yaml_lite.py` contains three independent hand-rolled character scanners — `_split_flow`, `_split_key`, `_strip_comment` — that each re-implement the same quote-state / backslash-escape / bracket-depth bookkeeping. Because the logic is copy-pasted rather than shared, the three keep drifting out of sync: four separate bug cards have patched them one at a time. Decision-gated on extracting one shared stepping primitive so the scanners cannot diverge again."
status: open
stage: null
contribution: medium
created: "2026-06-04T04:39:22Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - yaml-lite-strip-comment-defeated-by-unbalanced-quote-in-bare-value
  - yaml-lite-truncates-flow-collection-with-hash-in-quoted-element
  - yaml-lite-flow-collection-mis-splits-on-backslash-escaped-quote
  - strip-comment-closes-double-quoted-scalar-on-backslash-escaped-quote
  - yaml-lite-flow-collection-mis-splits-on-bare-quote-in-unquoted-element
  - openclaw-porter-fetch-hint-lands-outside-quoted-description-breaking-frontmatter-yaml
tags: [meta-fix, infra, api-contract]
definition_of_done: |
  - [ ] PROCESS: pick a factoring (see `## Decision required`) and record it in log.md with rationale.
  - [ ] MECHANICAL: the three scanners (`_split_flow`, `_split_key`, `_strip_comment`) share ONE quote/escape/depth stepping primitive; no scanner hand-rolls its own `in_q`/`escaped`/`depth` bookkeeping.
  - [ ] TDD: every existing yaml_lite regression test still passes unchanged (the four sibling-bug tests are the contract the shared primitive must preserve).
  - [ ] TDD: a single new test exercises the shared primitive directly so a future scanner reusing it inherits escape/quote correctness by construction.
  - [ ] PROCESS: `uv run goc validate` clean; `python scripts/sync_plugin_assets.py --check` green (vendored parser mirrored into plugin payloads).
---

# yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting

## Summary

`goc/_vendor/yaml_lite.py` contains three independent, hand-rolled
character scanners — `_split_flow`, `_split_key`, and `_strip_comment`
— that each re-implement the same quote-state / backslash-escape /
bracket-depth bookkeeping. Because the logic is copy-pasted rather
than shared, the three keep drifting out of sync: a fix applied to one
is silently missing from another. Four separate bug cards have now
patched these scanners one at a time. This is the missing-abstraction
signal — extract one shared stepping primitive so the scanners cannot
diverge again.

## What's broken (the recurring shape)

Three loops, three copies of the same state machine:

- `_split_flow` (`yaml_lite.py:445`) — tracks `in_q`, `escaped`, `depth`.
- `_split_key` (`yaml_lite.py:505`) — tracks `in_q`, `escaped`.
- `_strip_comment` (`yaml_lite.py:528`) — tracks `in_q`, `depth`, and
  (as of the most recent fix) `escaped`.

Each was fixed independently as its own defect surfaced:

1. [yaml-lite-strip-comment-defeated-by-unbalanced-quote-in-bare-value](../yaml-lite-strip-comment-defeated-by-unbalanced-quote-in-bare-value/)
   — `_strip_comment` quote-gating.
2. [yaml-lite-truncates-flow-collection-with-hash-in-quoted-element](../yaml-lite-truncates-flow-collection-with-hash-in-quoted-element/)
   — `_strip_comment` flow-gating.
3. [yaml-lite-flow-collection-mis-splits-on-backslash-escaped-quote](../yaml-lite-flow-collection-mis-splits-on-backslash-escaped-quote/)
   — `_split_flow` escape handling.
4. [strip-comment-closes-double-quoted-scalar-on-backslash-escaped-quote](../strip-comment-closes-double-quoted-scalar-on-backslash-escaped-quote/)
   — `_strip_comment` escape handling (the fix card #3 *claimed* was
   already present but wasn't).

Card #4's body documents the smoking gun: card #3's DoD asserted the
escape fix had been "already applied to `_strip_comment`," but it
hadn't — exactly the failure mode copy-pasted state machines produce.
Each scanner is one forgotten arm away from the next silent
round-trip-corruption bug.

## Why it matters

`yaml_lite` is the vendored frontmatter parser every `goc` read goes
through, and it is mirrored byte-for-byte into all three plugin
payloads (`claude-plugin/goc/`, `codex-plugin/goc/`,
`openclaw-plugin/goc/`). A drift bug in any scanner silently corrupts
authored card content on round-trip and ships to consumers. The
per-instance fix rate (4 cards) is the cost of the duplication; the
abstraction pays it down once.

## Decision required

The fix is a refactor, and the right factoring is a judgment call.
Options:

- **(A) Shared stepping function.** A `_scan(text)` generator yielding
  `(index, char, in_quote, depth)` tuples that encapsulates quote +
  escape + bracket-depth transitions once. The three scanners consume
  it and only decide *what to do* at each position (split on comma,
  split on `:`, terminate on `#`). Maximum dedup; changes each
  scanner's inner loop shape.
- **(B) Shared `QuoteState` helper class.** A small stateful object
  with a `.feed(char)` method returning the post-transition state
  (`in_quote`, `escaped`, `depth`). Scanners keep their own `for`
  loops but delegate the bookkeeping. Smaller diff per scanner, the
  state machine lives in one place.
- **(C) Leave as-is, add a contract test only.** Accept the
  duplication; add one parametrized test that feeds the same
  escape/quote/depth corpus through all three scanners and asserts
  consistent quote-boundary detection, so the *next* drift turns a
  build red even if the code stays copy-pasted.

Trade-off: (A) removes the most duplication but is the largest,
riskiest diff against a parser with subtle established behavior; (B)
is the moderate middle; (C) is cheapest and lowest-risk but leaves the
duplication standing (drift still possible, just caught faster).

Recommendation to consider: **(B)** — it collapses the three state
machines into one without reshaping each scanner's control flow, so
the four existing regression tests remain the exact contract and the
diff stays auditable. Defer to maintainer judgment on risk appetite
vs. dedup.

## Fix

Determined once the factoring above is chosen. Whichever option lands,
the four existing sibling-bug tests are the non-negotiable contract:
they must pass unchanged, since they encode the precise quote/escape
behavior the refactor must preserve.

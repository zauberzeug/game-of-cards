---
title: frontmatter-emitter-does-not-quote-indicator-or-whitespace-padded-values
summary: "`emit_frontmatter` decides when to quote a scalar via the `_YAML_NEEDS_QUOTE` predicate, which omits two cases the vendored parser cares about: values that BEGIN with a YAML indicator char (`*`, `&`, etc.) and values with leading/trailing whitespace. A `*`/`&`-leading value is emitted bare, then the next parse of that same frontmatter CRASHES with `anchors/aliases not supported`. A whitespace-padded value is emitted bare and silently stripped on re-parse — silent data loss. The emit→parse round-trip is not closed."
status: open
stage: null
contribution: medium
created: "2026-05-26T20:20:14Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — a `*`/`&`-leading value and a whitespace-padded value both survive an emit->parse round-trip unchanged.
  - [ ] TDD: the quote-trigger predicate quotes values beginning with any YAML indicator char the vendored parser treats specially (at minimum `*` and `&`; review the full indicator set the parser rejects/interprets).
  - [ ] TDD: the quote-trigger predicate quotes values with leading or trailing whitespace.
  - [ ] MECHANICAL: fix lands in `goc/engine.py` (`_YAML_NEEDS_QUOTE` / `_yaml_inline`); no behavior change for already-correctly-quoted values.
  - [ ] TDD: `uv run goc validate` passes on this repo's deck.
---

# Frontmatter emitter doesn't quote indicator-leading or whitespace-padded values

## Location

`goc/engine.py:169` — the `_YAML_NEEDS_QUOTE` regex — consumed by
`_yaml_inline` at `goc/engine.py:187`.

## What's broken

`emit_frontmatter` writes scalars bare unless `_YAML_NEEDS_QUOTE`
matches. That predicate covers the structural cases (colon-space,
leading `#`, etc.) but misses two classes the **vendored parser** treats
specially:

1. **Values beginning with a YAML indicator char** (`*` alias, `&`
   anchor, and friends). The parser explicitly rejects `*`/`&`-leading
   bare scalars with `FrontmatterError: anchors/aliases not supported`.
   The emitter writes them bare, so the *very next* parse of the
   emitted frontmatter crashes. The emit->parse round-trip is not closed.

2. **Values with leading or trailing whitespace.** YAML strips
   surrounding whitespace from bare scalars on parse. The emitter writes
   them bare, so the padding is silently lost on re-parse — silent data
   corruption rather than a crash.

This is one root cause: the quote-trigger predicate is an
under-specified subset of "values the parser will not round-trip bare."

## Empirical evidence

`reproduce.py` output (exit 1 = defect fires):

```
=== '* asterisk start' ===
  emitted: 'summary: * asterisk start'
  CRASH on re-parse: FrontmatterError: YAML parse error inside frontmatter: line 3: anchors/aliases not supported
=== '&anchor start' ===
  emitted: 'summary: &anchor start'
  CRASH on re-parse: FrontmatterError: YAML parse error inside frontmatter: line 3: anchors/aliases not supported
=== 'trailing space ' ===
  emitted: 'summary: trailing space '
  DRIFT on re-parse: got 'trailing space' (lost trailing whitespace)
=== ' leading space' ===
  emitted: 'summary:  leading space'
  DRIFT on re-parse: got 'leading space' (lost leading whitespace)
```

## Why it matters

Every card mutation that rewrites frontmatter (`goc new`, `status`,
`done`, `advance`, `move`, `decide`, `wait`, …) round-trips through
`emit_frontmatter` -> `parse_frontmatter`. A card whose `summary` (or any
string field) legitimately starts with `*` — e.g. a summary opening with
markdown emphasis, or a literal `* `-bulleted phrase — is filable, but
the next command that touches that card crashes the engine on its own
output. The whitespace case is quieter but worse: the data is silently
altered, and `goc validate` won't flag it because the re-parsed
frontmatter is still well-formed. The companion cards
[replace-pyyaml-with-vendored-parser](../replace-pyyaml-with-vendored-parser/)
and [yaml-lite-empty-block-scalar-consumes-next-key](../yaml-lite-empty-block-scalar-consumes-next-key/)
hardened the *parser*; this card closes the *emitter* side of the same
round-trip contract.

## Fix

Extend the quote-trigger predicate so `_yaml_inline` quotes (and
escapes) any scalar that begins with a YAML indicator char the parser
treats specially, and any scalar with leading or trailing whitespace.
Reuse the existing quoting path already applied to colon-bearing values
— the emitter already knows how to quote; it just doesn't recognize
these two triggers. Do not change emission for values that already
round-trip bare.

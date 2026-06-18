---
title: frontmatter-emitter-leaves-folded-block-scalar-headers-unquoted
status: done
stage: null
contribution: medium
created: "2026-06-18T05:01:22Z"
closed_at: "2026-06-18T05:05:23Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
summary: |
  The emitter quote-trigger regex allows an explicit-indent digit run on the
  pipe (|2) branch but not the folded (>2) branch, while the yaml-lite parser
  recognizes both. A scalar value like ">2" is emitted bare and crashes the
  card on the next re-parse with FrontmatterError.
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — every folded-with-explicit-indent value (>2, >3, >10, >2-, >2+) round-trips through emit_frontmatter → parse_frontmatter unchanged
  - [x] TDD: a regression test in tests/ asserts emit→parse round-trip for the folded-with-digits family alongside the existing pipe-family cases
  - [x] MECHANICAL: _YAML_BLOCK_HEADER_RE folded branch mirrors the pipe branch (allows \d*), and the full regression suite stays green
worker: {who: "claude[bot]", where: main}
---

# frontmatter-emitter-leaves-folded-block-scalar-headers-unquoted

## Location

- Bug site: `goc/engine.py:186` — `_YAML_BLOCK_HEADER_RE`, consumed by the
  quote-trigger in `_yaml_inline` at `goc/engine.py:247`.
- Counterpart that makes it crash: `goc/_vendor/yaml_lite.py:42` —
  `_FOLDED_INDICATOR_RE`, which raises at `goc/_vendor/yaml_lite.py:263-264`.

## What's broken

The emitter's block-scalar-header quote-trigger is asymmetric. The pipe
(literal) branch allows an explicit-indent digit run; the folded branch does
not:

```python
# goc/engine.py:186
_YAML_BLOCK_HEADER_RE = re.compile(r"^(?:\|\d*[-+]?|>[-+]?)$")
#                                       ^^^ pipe: has \d*   ^^^ folded: NO \d*
```

But the parser's folded recognizer *does* accept the digits:

```python
# goc/_vendor/yaml_lite.py:42
_FOLDED_INDICATOR_RE = re.compile(r"^>(\d+)?([-+]?)$")
```

So a scalar value of exactly `">2"` (also `">3"`, `">10"`, `">2-"`, `">2+"`)
is not recognized as a block header by the emitter, gets written bare as
`summary: >2`, and on the next read the parser recognizes `>2` as a folded
block-scalar header and raises:

```
FrontmatterError: YAML parse error inside frontmatter: line N: folded scalars (>) not supported
```

The pipe siblings (`|2`, `|3`, `|2-`) are correctly quoted and round-trip
fine — only the folded-with-digits set leaks.

## Empirical evidence

`reproduce.py` output on a clean checkout (pre-fix):

```
  '>2'     emitted as 'summary: >2'          round-trip: CRASH: FrontmatterError: ... folded scalars (>) not supported
  '>3'     emitted as 'summary: >3'          round-trip: CRASH: FrontmatterError: ... folded scalars (>) not supported
  '>10'    emitted as 'summary: >10'         round-trip: CRASH: FrontmatterError: ... folded scalars (>) not supported
  '>2-'    emitted as 'summary: >2-'         round-trip: CRASH: FrontmatterError: ... folded scalars (>) not supported
  '>2+'    emitted as 'summary: >2+'         round-trip: CRASH: FrontmatterError: ... folded scalars (>) not supported
  '|2'     emitted as 'summary: "|2"'        round-trip: OK
  '|3'     emitted as 'summary: "|3"'        round-trip: OK
  '|2-'    emitted as 'summary: "|2-"'       round-trip: OK

DEFECT REPRODUCED: 5 value(s) failed round-trip: ['>2', '>3', '>10', '>2-', '>2+']
```

## Why it matters

`_yaml_inline` is the inline-scalar emitter used by `emit_frontmatter` for
every flat string field (`title`, `summary`, `created`, …). Every mutating
verb (`status`, `done`, `wait`, `move`, `decide`, `quality-pass`, …) rewrites
the whole card through `emit_frontmatter`. A `summary` (or any free-text
field) authored or pasted as the two characters `>2` is unusual but fully
valid input — the reachability path is: one-shot-authored card with
`summary: ">2"` → any mutating verb re-emits it bare → the *next* read
(`load_card_or_exit`, `goc validate`, board/table render) crashes with a
`FrontmatterError`.

This is strictly worse than an ordinary "needs quoting" miss: the parser was
deliberately hardened (closed card
`yaml-lite-folded-scalar-with-chomp-or-indent-indicator-misparses`) to
*raise* on `>2`, so the emitter gap now manifests as a hard crash rather than
silent corruption.

The closed sibling
[frontmatter-emitter-leaves-explicit-indent-block-scalar-headers-unquoted](../frontmatter-emitter-leaves-explicit-indent-block-scalar-headers-unquoted/)
fixed the *pipe* forms (`|2`, `|3`, `|2-`, `|2+`, `|10`) but shipped exactly
the regex with the missing `\d*` on the folded branch — its DoD round-trip
test enumerated only the pipe family, so the folded-with-digits case slipped
through.

## Fix

Make the folded branch mirror the pipe branch by adding `\d*`:

```python
# goc/engine.py:186
_YAML_BLOCK_HEADER_RE = re.compile(r"^(?:\|\d*[-+]?|>\d*[-+]?)$")
```

Add a round-trip regression test covering `>2`, `>3`, `>10`, `>2-`, `>2+`
alongside the existing pipe-family cases.

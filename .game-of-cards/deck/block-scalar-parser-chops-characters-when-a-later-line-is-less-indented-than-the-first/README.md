---
title: block-scalar-parser-chops-characters-when-a-later-line-is-less-indented-than-the-first
summary: "`_parse_block_scalar` locked `block_indent` to the first content line's indent, then sliced every subsequent line with `raw[block_indent:]`. A later line indented less than the first (but still deeper than the block declaration) had real leading characters chopped off instead of ending the block (YAML spec behavior). Parse-only — the emitter always indents uniformly by 2, so this bit hand-edited or externally-authored frontmatter, not goc's own emit output. Fixed: such a line now raises a ParseError instead of silently corrupting."
status: done
stage: null
contribution: low
created: "2026-05-26T21:57:44Z"
closed_at: 2026-05-26T22:06:53Z
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — a block scalar whose second content line is less-indented than the first parses without silently eating characters (either the block ends at that line per YAML spec, or a ParseError is raised).
  - [x] MECHANICAL: fix lands in `goc/_vendor/yaml_lite.py` `_parse_block_scalar`.
  - [x] TDD: `uv run goc validate` passes; existing block-scalar regression cards still pass.
worker: {who: "claude[bot]", where: main}
---

# Block-scalar parser chops characters when a later line is less-indented than the first

## Verified bug (reproduce.py exits 1 against the unfixed parser)

`goc/_vendor/yaml_lite.py` `_parse_block_scalar`:

```python
if block_indent is None:
    block_indent = curr
chunks.append(raw[block_indent:])
```

`block_indent` was fixed to the **first** content line's indentation. The loop
continued as long as `curr > declaration_indent`. A subsequent line whose indent
was between `declaration_indent` and the first line's indent was still admitted
to the block, then sliced with `raw[block_indent:]` — removing real content
characters rather than indentation. The reproducer confirmed
`k: |\n    deep line\n  shallow line\nnext: x` parsed to
`{'k': 'deep line\nallow line\n', ...}` — the leading `sh` of `shallow` eaten.

Per the YAML spec, the block scalar's indentation is set by the first non-empty
line; a line less-indented than that ends the block. Such a line is also
over-indented relative to the declaration's parent, so it cannot be a clean
sibling key either — it is unambiguously malformed.

## Fix

`_parse_block_scalar` now raises a `ParseError` when a non-blank content line is
indented strictly less than the established `block_indent` (and more than the
declaration). Rejecting is the honest outcome: the line can neither be valid
block content nor a clean sibling, and silently slicing it corrupts data. Blank
lines are unaffected (they never set `block_indent`), and goc's own uniformly
indented emit output never hits the new branch, so there is no round-trip
regression.

## Why this was parked as parse-only

`_emit_block_field` always indents every content line by exactly 2, so goc's own
emit output never triggers this. It can only bite frontmatter authored or
hand-edited outside goc — sibling of the round-trip bug
[block-scalar-parser-strips-trailing-whitespace-breaking-emit-parse-round-trip](../block-scalar-parser-strips-trailing-whitespace-breaking-emit-parse-round-trip/).

## Falsification recipe

```python
from goc._vendor import yaml_lite
out = yaml_lite.safe_load("k: |\n    deep line\n  shallow line\nnext: x\n")
# Prediction: out["k"] == "deep line\nallow line\n"  (the "sh" of "shallow" is eaten)
# Correct behavior: either the block ends at "shallow line" (k == "deep line\n",
# and "shallow line" is a parse error / separate construct) or a ParseError.
assert out["k"].splitlines()[1] == "shallow line", out
```

Surfaced by a general-purpose hunter agent during an audit-deck pass.

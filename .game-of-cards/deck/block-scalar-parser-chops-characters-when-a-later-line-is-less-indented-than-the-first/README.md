---
title: block-scalar-parser-chops-characters-when-a-later-line-is-less-indented-than-the-first
summary: "UNVERIFIED. `_parse_block_scalar` locks `block_indent` to the first content line's indent, then slices every subsequent line with `raw[block_indent:]`. A later line indented less than the first (but still deeper than the block declaration) gets real leading characters chopped off instead of ending the block (YAML spec behavior). Parse-only — the emitter always indents uniformly by 2, so this bites hand-edited or externally-authored frontmatter, not goc's own emit output."
status: open
stage: null
contribution: low
created: "2026-05-26T21:57:44Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, unverified]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — a block scalar whose second content line is less-indented than the first parses without silently eating characters (either the block ends at that line per YAML spec, or a ParseError is raised).
  - [ ] MECHANICAL: fix lands in `goc/_vendor/yaml_lite.py` `_parse_block_scalar`.
  - [ ] TDD: `uv run goc validate` passes; existing block-scalar regression cards still pass.
---

# Block-scalar parser chops characters when a later line is less-indented than the first

## Hypothesis (unverified — no reproduce.py budget this round)

`goc/_vendor/yaml_lite.py:171-173`:

```python
if block_indent is None:
    block_indent = curr
chunks.append(raw[block_indent:].rstrip())
```

`block_indent` is fixed to the **first** content line's indentation. The loop
continues as long as `curr > declaration_indent` (line 169). A subsequent line
whose indent is between `declaration_indent` and the first line's indent is
still admitted to the block, then sliced with `raw[block_indent:]` — which
removes real content characters rather than indentation.

Per the YAML spec, the block scalar's indentation is set by the first
non-empty line; a line less-indented than that should terminate the block. The
current code neither terminates nor errors — it silently corrupts.

## Why deferred

Parse-only. `_emit_block_field` (`goc/engine.py:225-231`) always indents every
content line by exactly 2, so goc's own emit output never triggers this. It can
only bite frontmatter authored or hand-edited outside goc. Lower realism than
the sibling round-trip bug
[block-scalar-parser-strips-trailing-whitespace-breaking-emit-parse-round-trip](../block-scalar-parser-strips-trailing-whitespace-breaking-emit-parse-round-trip/),
so parked rather than filed with a reproducer this round.

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

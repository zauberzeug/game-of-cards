---
title: frontmatter-emitter-leaves-explicit-indent-block-scalar-headers-unquoted
summary: "`emit_frontmatter`'s quote-trigger gates on the frozenset `_YAML_BLOCK_TOKENS = {'|', '|-', '|+', '>', '>-', '>+'}`, but the vendored parser's `_BLOCK_INDICATOR_RE = ^\\|(\\d+)?([-+]?)$` also accepts explicit-indent variants `|2`, `|3`, `|2-`, `|2+`, `|10`, etc. A scalar field whose value is one of those tokens is emitted bare, then re-parsed as a literal block scalar with the indicated indent and empty content — silent data loss on round-trip."
status: done
stage: null
contribution: high
created: "2026-05-30T04:32:33Z"
closed_at: "2026-05-30T04:38:31Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — a scalar value of `|2`, `|3`, `|2-`, `|2+`, and `|10` each survives an `emit_frontmatter` -> `parse_frontmatter` round-trip unchanged.
  - [x] TDD: the quote-trigger predicate quotes any scalar that matches the parser's `_BLOCK_INDICATOR_RE` (bare `|` and the explicit-indent set are both covered).
  - [x] MECHANICAL: fix lands in `goc/engine.py` near `_YAML_BLOCK_TOKENS` / `_yaml_inline`; no behavior change for already-correctly-quoted values.
  - [x] TDD: `uv run python -m unittest discover -s tests` passes.
  - [x] TDD: `uv run goc validate` passes on this repo's deck.
worker: {who: "claude[bot]", where: main}
---

# Frontmatter emitter leaves explicit-indent block-scalar headers unquoted

## Location

`goc/engine.py:182` — the `_YAML_BLOCK_TOKENS` frozenset — consumed
by the quote-trigger predicate inside `_yaml_inline` at
`goc/engine.py:232`.

## What's broken

`emit_frontmatter` decides whether to quote a scalar by checking
`_YAML_NEEDS_QUOTE`, the integer/null/bool coercion predicate, the
indicator-leading set, leading/trailing whitespace, and
`_YAML_BLOCK_TOKENS`:

```python
# goc/engine.py:181-182
# Whole-value tokens the parser interprets as block/folded scalar indicators.
_YAML_BLOCK_TOKENS = frozenset({"|", "|-", "|+", ">", ">-", ">+"})
```

That frozenset enumerates only the bare-indicator forms. The vendored
parser, however, recognizes the **explicit-indent** form too:

```python
# goc/_vendor/yaml_lite.py:36-38
# Literal block scalar header: `|`, with an optional explicit indentation
# indicator (`|2`) and an optional chomping indicator (`-` strip / `+` keep).
_BLOCK_INDICATOR_RE = re.compile(r"^\|(\d+)?([-+]?)$")
```

`|2`, `|3`, `|2-`, `|2+`, `|10`, `|12+` all match `_BLOCK_INDICATOR_RE`
but none are in `_YAML_BLOCK_TOKENS`. The emitter writes them bare;
the parser then reads the bare token as a block-scalar header with the
indicated indent and **empty content** — the original string is gone.

This is the same shape as the closed sibling
[frontmatter-emitter-does-not-quote-indicator-or-whitespace-padded-values](../frontmatter-emitter-does-not-quote-indicator-or-whitespace-padded-values/):
the quote-trigger predicate is an under-specified subset of "values
the parser will not round-trip bare." That card extended the predicate
for `*`/`&`-leading and whitespace-padded values; this card extends it
for the explicit-indent block-scalar headers the parser also accepts.

## Empirical evidence

`reproduce.py` output (exit 1 = defect fires):

```
=== '|2' ===
  emitted line: 'summary: |2'
  round-trip got: '' (lost original value)
=== '|3' ===
  emitted line: 'summary: |3'
  round-trip got: '' (lost original value)
=== '|2-' ===
  emitted line: 'summary: |2-'
  round-trip got: '' (lost original value)
=== '|2+' ===
  emitted line: 'summary: |2+'
  round-trip got: '' (lost original value)
=== '|10' ===
  emitted line: 'summary: |10'
  round-trip got: '' (lost original value)
```

## Why it matters

Every card mutation that rewrites frontmatter (`goc new`, `status`,
`done`, `attest`, `advance`, `unadvance`, `move`, `decide`, `wait`,
`repair-edges`, `quality-pass`, `migrate`, `migrate-list-style`)
round-trips through `emit_frontmatter` -> `parse_frontmatter`.
`migrate-list-style` is the worst case: it re-emits **every** card in
the deck in one pass.

**Reachability path.** A card whose `summary`, `worker.who`, or any
string field literally equals `|2` / `|3` / `|10` / `|2-` / `|2+` is
filable today — `goc new --summary "|2"` would scaffold one without
complaint. The next state-flip verb that touches that card silently
empties the field. Likely real-world producers: a hand-edited
frontmatter value summarizing a markdown table column width
("`|2`-wide gutter"), an LLM-generated `quality-pass --llm` summary
rewrite that happens to land on one of these strings, or a card filed
with a stand-in placeholder string later replaced with a real summary.

Closure of the emit -> parse round-trip is the load-bearing invariant
for every verb that rewrites frontmatter; an under-specified quote
trigger is a silent-data-loss surface.

## Fix

Replace the frozenset membership check with a regex check that
covers both the bare-indicator forms and the explicit-indent forms.
Concretely, in `goc/engine.py`:

```python
# Replace _YAML_BLOCK_TOKENS frozenset (line 181-182) with a regex.
# `|` with optional digit-indent and optional chomp indicator,
# plus `>` and its chomp variants (folded scalar — the parser rejects
# folded scalars but we still quote so the bare token isn't re-read
# as one once folded support lands).
_YAML_BLOCK_HEADER_RE = re.compile(r"^(?:\|\d*[-+]?|>[-+]?)$")
```

Then at `engine.py:232` swap `s in _YAML_BLOCK_TOKENS` for
`bool(_YAML_BLOCK_HEADER_RE.match(s))`. This both covers the
explicit-indent variants and remains coupled to the parser's own
recognizer shape — the same "derive by reference from the parser"
discipline already used by `_parser_coerces_scalar` (engine.py:185-202).

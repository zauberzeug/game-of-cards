---
title: emit-frontmatter-always-strips-trailing-newline-from-multi-line-string-fields
status: active
stage: null
contribution: medium
created: "2026-06-08T05:01:18Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
summary: |
  `emit_frontmatter` writes every multi-line string field other than
  `definition_of_done` with the strip block indicator (`|-`), regardless of
  whether the value ends in a newline. The vendored parser reads a clip block
  (`|`) back WITH one trailing newline, so a card authored as `summary: |`
  (the natural style `goc new` and humans produce) is silently rewritten to
  `summary: |-` and loses its trailing newline on the first re-emit — an
  unrelated-field mutation fired by any verb that re-emits frontmatter
  (`wait`, `decide`, `advance`, `migrate-list-style`, ...).
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — an authored `summary: |` clip block survives an emit->parse round-trip with its trailing newline AND its `|` indicator intact.
  - [ ] TDD: a value with no trailing newline still emits `|-` and round-trips faithfully (the fix selects the indicator from the value, it does not blanket-switch to `|`).
  - [ ] TDD: regression test added under tests/ covering both trailing-newline states for a multi-line string field through emit_frontmatter.
  - [ ] MECHANICAL: the `emit_frontmatter` docstring no longer claims "Other multi-line strings use `|-`"; it documents the value-derived indicator choice.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` pass.
worker: {who: "claude[bot]", where: main}
---

# emit-frontmatter always strips the trailing newline from multi-line string fields

## Location

`goc/engine.py:326-328` — the multi-line-string branch of `emit_frontmatter`:

```python
if isinstance(value, str) and "\n" in value:
    lines.extend(_emit_block_field(key, value, indicator="|-"))
    continue
```

Contrast the `definition_of_done` branch immediately above
(`goc/engine.py:315-316`), which correctly uses the clip indicator:

```python
if key == "definition_of_done":
    lines.extend(_emit_block_field(key, value or "", indicator="|"))
```

## What's broken

`_emit_block_field` (`engine.py:269`) `rstrip("\n")`s the value and re-emits the
content lines verbatim; the only thing the indicator controls is whether the
**parser** re-adds a trailing newline on the way back in:

- `|` (clip) → parser returns the value WITH exactly one trailing `\n`.
- `|-` (strip) → parser returns the value WITHOUT a trailing `\n`.

So the indicator must match the value's actual trailing-newline state for the
round-trip to be faithful. The emitter ignores that and hard-codes `|-` for
every multi-line string field except `definition_of_done`. The docstring even
enshrines the bug:

> Other multi-line strings use `|-` block style.

A card authored with `summary: |` (clip) parses to a value ending in `\n`.
On the first re-emit, that value is written back as `summary: |-`, and the
reparsed value loses its trailing newline. Two observable mutations on a field
no verb touched:

1. the on-disk block indicator flips `|` → `|-`, and
2. the parsed value drops its trailing newline.

This is distinct from the closed
[block-scalar-parser-strips-trailing-whitespace-breaking-emit-parse-round-trip](../block-scalar-parser-strips-trailing-whitespace-breaking-emit-parse-round-trip/),
which round-tripped from goc-**emitted** form (already `|-`) and explicitly set
aside the single clip-mode trailing newline as correct YAML. The defect here is
the emitter's **indicator choice** for authored clip blocks, not the parser's
content-line whitespace handling.

## Empirical evidence

`uv run python deck/emit-frontmatter-always-strips-trailing-newline-from-multi-line-string-fields/reproduce.py`:

```
authored summary (parsed): 'line one\nline two\n'
re-emitted summary (parsed): 'line one\nline two'
indicator flipped | -> |-: True
trailing newline dropped: True
no-trailing-newline value round-trips faithfully: True

FAIL: emit_frontmatter mutates an authored multi-line string field.
```

A live-deck sweep confirms reachability: of the 24 cards with block-style
summaries, all but one are already stored as `summary: |-` — they were authored
or migrated as `|` and silently flipped by routine verbs. The single survivor
(`scheduler-tiebreak-undercounts-downstream-flow-through-filtered-out-cards`)
still carries `summary: |` and will mutate the next time it is advanced, waited,
repaired, or migrated.

## Why it matters

`emit_frontmatter` is the single write path for every state-changing verb
(`goc wait`, `decide`, `advance`/`unadvance`, `status --by`, `repair-edges
--apply`, `quality-pass`, and `migrate-list-style`, which re-emits every card).
Any of them touching a card whose `summary` is still a `|` clip block produces a
spurious frontmatter diff and a non-idempotent rewrite — the same
"editing one field rewrites an unrelated field" anti-pattern tracked elsewhere,
and it breaks `migrate-list-style`'s advertised idempotence. The reachability
path is the authoring tool itself: `goc new` / `create-card` write multi-line
`summary` blocks in clip (`|`) style, so the offending input shape is produced
by shipping code, not just hand edits.

## Fix

Select the block indicator from the value's trailing-newline state instead of
hard-coding `|-` (`engine.py:326-328`):

```python
if isinstance(value, str) and "\n" in value:
    indicator = "|" if value.endswith("\n") else "|-"
    lines.extend(_emit_block_field(key, value, indicator=indicator))
    continue
```

This is faithful both ways — a `\n`-terminated value emits `|` (parser re-adds
the newline) and a non-terminated value emits `|-` (parser adds none) — so
`emit_frontmatter(parse_frontmatter(text)) == text` for both authored styles.
`definition_of_done` keeps its dedicated `|` branch. The fix direction matches
every prior emitter-round-trip card in this repo (e.g.
[inline-emitter-writes-multi-line-strings-bare-destroying-subsequent-frontmatter](../inline-emitter-writes-multi-line-strings-bare-destroying-subsequent-frontmatter/),
[frontmatter-emitter-mangles-block-scalar-values-that-carry-leading-whitespace](../frontmatter-emitter-mangles-block-scalar-values-that-carry-leading-whitespace/)),
all closed at gate `none` in favour of preserving authored content — so no
human decision is required here.

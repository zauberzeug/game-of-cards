---
title: frontmatter-re-drops-trailing-blank-line-of-final-keep-block-scalar
summary: "`parse_frontmatter`'s `FRONTMATTER_RE` lets the `\\n---` closing delimiter swallow the trailing blank line of a `|+` (keep) block scalar that is the LAST frontmatter field, so the value reads back one newline short. This is the parse-side mirror of the closed emitter-side keep fix, which the emitter now writes correctly but the parser cannot round-trip."
status: done
stage: null
contribution: medium
created: "2026-06-25T19:59:31Z"
closed_at: "2026-06-25T20:09:48Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (a `|+` block scalar that is the final frontmatter field round-trips its trailing blank line through emit → parse)
  - [x] TDD: regression test added to tests/ covering the last-field-before-`---` keep-scalar round-trip
  - [x] MECHANICAL: bodies that themselves contain `---`, `|-`/`|` scalars, and bare-scalar frontmatter still parse with body intact (no regression)
  - [x] PROCESS: log.md records the fix and the relationship to the closed emitter-side card
  - [x] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# FRONTMATTER_RE drops the trailing blank line of a final `|+` keep block scalar

## Location

`goc/engine.py:136` — the document-level frontmatter splitter `FRONTMATTER_RE`,
consumed by both `parse_frontmatter` (`engine.py:159`) and
`mutate_frontmatter_field` (`engine.py:439`). The original (buggy) regex was:

```python
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)
```

## What's broken

The non-greedy `(.*?)\n---` stops at the *first* `\n---`. When a `|+`
(keep) block scalar that ends in a blank line is the **last**
frontmatter field, the document looks like:

```
---
title: x
summary: |+
  ends with blank

---
```

The scalar's trailing blank-line `\n` is immediately followed by the
closing `---`, so the regex's `\n---` delimiter consumes that newline.
The captured YAML group ends at `...ends with blank\n` (one newline),
and `yaml_lite` — which honors the `|+` keep indicator faithfully when
given the bytes — reads the value back as `'ends with blank\n'`. The
final blank line is silently dropped.

This is the **parse-side** counterpart of the already-closed
`emit-frontmatter-drops-trailing-blank-lines-from-multi-line-string-fields`,
which fixed `|+` selection in `emit_frontmatter`. That card's
`reproduce.py` docstring explicitly scoped this out:

> A keep block placed immediately before the closing `---` hits a
> separate parse-boundary defect in FRONTMATTER_RE + safe_load that
> this card does not address.

So the emitter now correctly writes `|+`, but `parse_frontmatter`
cannot read it back when the keep scalar is the final field.

## Empirical evidence

Before the fix, the final keep scalar lost its blank line:

```
$ uv run python -c "from goc.engine import emit_frontmatter, parse_frontmatter; fm={'title':'x','summary':'ends with blank\n\n'}; print(repr(parse_frontmatter(emit_frontmatter(fm))[0].get('summary')))"
'ends with blank\n'          # buggy — expected 'ends with blank\n\n'
```

After the fix, `reproduce.py` exits zero — the round-trip is faithful,
a body containing `---` still splits correctly, and a non-final keep
scalar (the control) is unaffected.

The loss was specific to the last-field position: add any sibling key
*after* `summary` and the value already round-tripped, because the
closing `\n---` then sat after the sibling, not after the blank line.

## Why it matters (reachability)

The emitter at `goc/engine.py` (`emit_frontmatter`) now selects the
`|+` keep indicator for any string field whose value ends in a blank
line, and writes frontmatter fields in schema order — `summary` and
other multi-line text fields can land last (before `advanced_by`/`tags`
when those are empty `[]`, the emitter still places them, but a
hand-authored or future card whose final emitted field is a keep
scalar hits this directly). Any mutation verb that re-emits a card
(`goc wait` / `decide` / `advance` / `migrate-list-style` / `status`)
runs the value through emit → parse on the next read; a final keep
scalar is silently shortened by one blank line per round-trip,
eventually diverging from the authored content.

## Fix (applied)

Widened the capture so trailing blank lines are handed to `yaml_lite`
(which already chomps per the `|`/`|-`/`|+` indicator) instead of being
eaten by the delimiter:

```python
FRONTMATTER_RE = re.compile(r"^---\n(.*?)(\n+)---[ \t]*(?:\n(.*))?$", re.DOTALL)
```

- `parse_frontmatter` now feeds `m.group(1) + m.group(2)` to `safe_load`
  and uses `m.group(3) or ""` as the body.
- `mutate_frontmatter_field` — the **second** `FRONTMATTER_RE` consumer
  (used by `goc decide`/`status`/`wait`) — read `m.group(2)` as the body,
  which the regroup turned into the blank-line run; left unchanged it
  destroyed the body on every gate flip. It now reads `group(2)` as the
  blank run and `group(3)` as the body, and re-emits the blank run between
  the frontmatter and `---`. For the common single-newline separator this
  reconstruction is byte-identical to the prior two-group behavior.

The non-greedy `(.*?)` still stops at the first delimiter run, so bodies
containing `---` are unaffected; `(\n+)` captures the blank line(s) the keep
indicator should preserve; `[ \t]*` tolerates trailing spaces on the
delimiter line; the optional `(?:\n(.*))?` handles the EOF-after-`---` case
(no trailing newline).

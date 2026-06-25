---
title: emit-frontmatter-drops-trailing-blank-lines-from-multi-line-string-fields
summary: "`emit_frontmatter` picks the block chomp indicator from only two options — `|` (clip) and `|-` (strip) — so a multi-line string field ending in a blank line (two-or-more trailing newlines) is emitted with `|` and read back with a single trailing newline, silently dropping the blank line(s). The fix is the missing third case: `|+` (keep). The vendored parser already supports `|+`; only the emit side never selects it."
status: done
stage: null
contribution: low
created: "2026-06-25T19:31:07Z"
closed_at: "2026-06-25T19:42:00Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — every multi-line string value ending in a blank line round-trips faithfully through emit_frontmatter -> parse_frontmatter
  - [x] TDD: a regression test in tests/ asserts `|+` (keep) round-trip for a `summary` ending in `\n\n`, including the leading-whitespace + trailing-blank case that forces the `|2+` explicit-indent header
  - [x] TDD: existing clip (`|`, single trailing newline) and strip (`|-`, no trailing newline) round-trips remain green, and `definition_of_done` (always `|`) is unaffected
  - [x] MECHANICAL: the `emit_frontmatter` docstring describes the three-way chomp selection
  - [x] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# emit_frontmatter drops trailing blank lines from multi-line string fields

## Location

`goc/engine.py:393` (chomp selection in `emit_frontmatter`) and the
supporting `_emit_block_field` at `goc/engine.py:303`.

## What's broken

`emit_frontmatter` chooses the block-scalar chomp indicator from only
two of YAML's three modes:

```python
# goc/engine.py:393
indicator = "|" if value.endswith("\n") else "|-"
```

`|` (clip) restores exactly one trailing newline on parse; `|-` (strip)
restores none. Neither preserves a *trailing blank line*. A value
ending in two-or-more newlines (`"foo\n\n"`) ends in `"\n"`, so it takes
the `|` branch and is read back as `"foo\n"` — the blank line is gone.

The third YAML mode, `|+` (keep), exists precisely for this: it
preserves every trailing blank line. The vendored parser already
implements it correctly:

```python
# goc/_vendor/yaml_lite.py:283
if chomp == "keep":
    # Preserve every trailing blank line plus the final line break.
    return "\n".join(chunks) + "\n"
```

But the emitter never selects it, and `_emit_block_field` unconditionally
`rstrip("\n")`s its input (`goc/engine.py:303`), so the trailing blank
content lines are dropped before they can be emitted.

The emitter's own docstring already states the intended contract —
"so the emit->parse round-trip is faithful" — which the blank-line case
violates.

## Empirical evidence

Before the fix, `uv run python deck/.../reproduce.py` showed every
blank-line-terminated value chomped to a single newline:

```
'foo\n\n'                                -> 'foo\n'                                  LOST
... 5/5 LOST
```

After the three-way chomp fix, the same reproduce exits 0:

```
'foo\n\n'                                -> 'foo\n\n'                                OK
'first line\nsecond line\n\n'            -> 'first line\nsecond line\n\n'            OK
'para one\n\npara two\n\n'               -> 'para one\n\npara two\n\n'               OK
'x\n\n\n'                                -> 'x\n\n\n'                                OK
'  indented first line\nmore\n\n'        -> '  indented first line\nmore\n\n'        OK

OK: all 5 values round-trip faithfully
```

(The reproduce uses values bounded by a following field — the realistic
shape, since a multi-line `summary` is never the last frontmatter field.
A keep block placed flush against the closing `---` hits a *separate*
parse-boundary limitation in `FRONTMATTER_RE` + `safe_load` that this
card does not address.)

## Why it matters

The reachability path: a hand-authored or externally-generated card
README whose `summary:` (or any multi-line string frontmatter field) is
written as a literal block ending in a blank line. The next mutation
verb that re-emits the frontmatter — `goc wait`, `goc decide`,
`goc advance`, `goc migrate-list-style`, all of which round-trip
through `emit_frontmatter` — silently rewrites the field, dropping the
authored blank line. This is the same fidelity class as the closed
[emit-frontmatter-always-strips-trailing-newline-from-multi-line-string-fields](../emit-frontmatter-always-strips-trailing-newline-from-multi-line-string-fields/)
(which fixed only the clip-vs-strip single-newline case) and the parser
side [yaml-lite-keep-chomping-indicator-treated-as-clip](../yaml-lite-keep-chomping-indicator-treated-as-clip/)
(which fixed `|+` *parsing* but noted the emitter still never emits it).
This card closes the remaining emit-side gap.

Impact is low: no GoC verb *produces* a trailing-blank-line frontmatter
value, so the bug bites only authored/external input flowing through a
re-emit. But the emitter's contract is faithful round-trip, and the
parser already honors `|+` — leaving emit half-done is the kind of
quiet asymmetry that makes the next round-trip card harder to reason
about.

## Fix

Make the chomp selection three-way in `emit_frontmatter`:

```python
if value.endswith("\n\n"):
    indicator = "|+"   # keep: preserve trailing blank line(s)
elif value.endswith("\n"):
    indicator = "|"    # clip: one trailing newline
else:
    indicator = "|-"   # strip: no trailing newline
```

and make `_emit_block_field` chomp-aware so the keep case does not
`rstrip("\n")` away the trailing blank content lines it must emit. For
`|+`, the content lines are exactly `value[:-1].split("\n")` (the parser
reads a keep block back as `"\n".join(chunks) + "\n"`); clip and strip
keep their existing `rstrip("\n").splitlines()` behavior. Both sites are
in `goc/engine.py`. `definition_of_done` (always passed `indicator="|"`)
is untouched.

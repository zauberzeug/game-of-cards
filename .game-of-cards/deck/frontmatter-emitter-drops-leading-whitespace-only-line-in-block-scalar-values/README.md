---
title: frontmatter-emitter-drops-leading-whitespace-only-line-in-block-scalar-values
summary: "`_emit_block_field` only emits an explicit indent indicator (`|2`/`|2-`) when the FIRST NON-BLANK content line begins with whitespace. A leading whitespace-only line (e.g. `\"   \"`) that precedes the first non-blank line is skipped by the `first_content` selection, so the bare `|`/`|-` indicator is kept; on re-parse the parser treats that line as a structural blank (`block_indent is None`) and collapses its interior spaces to `\"\"`. Breaks the emit->parse round-trip for the leading-whitespace case left unfixed by the two closed block-scalar siblings."
status: open
stage: null
contribution: medium
created: "2026-06-24T19:36:16Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — a block-scalar value whose first
        line is whitespace-only (`"   \nsecond line"`) round-trips
        (emit->parse) byte-for-byte, plus a multi-leading-blank variant
        (`"  \n   \nbody"`).
  - [ ] TDD: the already-fixed sibling cases still round-trip (interior
        whitespace-only line `"first\n   \nthird"`, first non-blank line
        indented, trailing-blank chomp) so the fix does not regress them.
  - [ ] MECHANICAL: the fix lands in the `goc/engine.py` source-of-truth
        (the engine is vendored into the plugin payloads); plugin mirrors
        re-sync and `python scripts/sync_plugin_assets.py --check` passes.
  - [ ] PROCESS: `uv run goc validate` is clean on this repo's own deck.
---

# Frontmatter emitter drops a leading whitespace-only line in block-scalar values

## Location

`goc/engine.py:287-307` — `_emit_block_field`.

## What's broken

`_emit_block_field` chooses the explicit YAML indentation indicator
(`|2` / `|2-`) only when the **first non-blank** content line begins
with whitespace:

```python
text = (value or "").rstrip("\n")
lines = text.splitlines()
first_content = next((ln for ln in lines if ln.strip()), "")
if first_content[:1].isspace():
    indicator = f"{indicator[0]}2{indicator[1:]}"
out = [f"{key}: {indicator}"]
for ln in lines:
    out.append(f"  {ln}" if ln else "")
return out
```

The `first_content` selection deliberately **skips whitespace-only
lines**. So a value whose first line is whitespace-only (e.g.
`"   \nsecond line"`) keeps the bare `|-` indicator. The emitter still
writes that line verbatim with its 2-space prefix (`"     "`), but
because no explicit indicator was emitted, the parser's `block_indent`
is `None` when it reaches that line. The vendored parser
(`goc/_vendor/yaml_lite.py:239-249`) then treats any `rstripped == ""`
line as a *structural blank* while `block_indent is None`:

```python
chunks.append("" if block_indent is None else raw[block_indent:])
```

so the 3 interior spaces collapse to `""` — the leading whitespace is
silently lost.

The explicit-indicator path is exactly the cure: when `|2` is emitted,
`block_indent` is preset to `declaration_indent + 2` (`yaml_lite.py:231`),
so the same line is sliced `raw[block_indent:]` and its interior spaces
survive. The emitter just never triggers it for this case.

## Empirical evidence

`uv run python deck/.../reproduce.py`:

```
FAIL '   \nsecond line' -> '\nsecond line'
FAIL '  \n   \nbody'    -> '\n\nbody'
OK   'first\n   \nthird' (interior case, already fixed, round-trips)
```

## Why it matters

`emit_frontmatter` (engine.py:332) routes any string field that
contains `"\n"` through `_emit_block_field`. Every read-then-re-emit
verb — `goc decide` (engine.py:5479), `goc quality-pass`,
`goc migrate-list-style` (engine.py:5737), `goc new` — rewrites the
whole frontmatter through this path. A card authored with an explicit
indicator and a leading whitespace-only line in `summary` /
`definition_of_done`, e.g.

```yaml
summary: |2-
     
  Real summary text here.
```

parses correctly the first time (author pinned the indent), but the
next verb that touches the card re-emits it with a bare `|-` and the
leading `"   "` line is silently de-whitespaced on the following parse.
This is the residual *leading*-whitespace case left open by the two
closed siblings:

- [frontmatter-emitter-mangles-block-scalar-values-that-carry-leading-whitespace](../frontmatter-emitter-mangles-block-scalar-values-that-carry-leading-whitespace/)
  — fixed only the FIRST-NON-BLANK-content-line-indented case (its
  `first_content` selection deliberately skips whitespace-only lines).
- [block-scalar-parser-collapses-whitespace-only-content-lines](../block-scalar-parser-collapses-whitespace-only-content-lines/)
  — fixed INTERIOR whitespace-only lines, but its fix explicitly keeps
  the `block_indent is None` short-circuit for leading blanks, which is
  exactly the unfixed path here.

## Fix

In `_emit_block_field`, also trigger the explicit indicator when a
whitespace-only-but-nonempty line precedes the first non-blank content
line (those are the lines the parser collapses while `block_indent` is
still `None`):

```python
text = (value or "").rstrip("\n")
lines = text.splitlines()
first_idx = next((i for i, ln in enumerate(lines) if ln.strip()), len(lines))
first_content = lines[first_idx] if first_idx < len(lines) else ""
# Pin the block indent with an explicit indicator when the value's own
# leading whitespace would otherwise be lost: either the first content
# line begins with whitespace, or a whitespace-only (but non-empty) line
# precedes it (the parser collapses such a line to "" while block_indent
# is still None).
if first_content[:1].isspace() or any(
    ln and not ln.strip() for ln in lines[:first_idx]
):
    indicator = f"{indicator[0]}2{indicator[1:]}"
```

Block emission only fires for multi-line values (`"\n" in value`), so a
bare single-line `"   "` is unaffected (it goes through `_yaml_inline`).

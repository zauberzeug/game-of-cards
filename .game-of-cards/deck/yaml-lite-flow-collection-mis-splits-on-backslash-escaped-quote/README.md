---
title: yaml-lite-flow-collection-mis-splits-on-backslash-escaped-quote
summary: "`_split_flow` in the vendored yaml-lite parser toggles quote state on every quote char with no backslash-escape awareness, so a flow mapping/sequence element containing an emitter-produced `\\\"` is mis-split: the comma after it is swallowed inside quote-mode and the following key/element is lost. Triggered on round-trip by a `worker` mapping whose value contains a literal double-quote. Sibling of the closed `_strip_comment` fix, which was repaired but `_split_flow` was not."
status: done
stage: null
contribution: low
created: "2026-05-27T11:25:27Z"
closed_at: "2026-05-27T11:31:32Z"
human_gate: none
advances:
  - yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — a `worker: {who: 'a"', where: 'b'}` mapping round-trips through `emit_frontmatter` → `parse_frontmatter` unchanged (both keys preserved, value exact).
  - [x] TDD: a flow sequence element containing an escaped double-quote (e.g. a tag-like list `["x\"y", "z"]`) also splits correctly and round-trips.
  - [x] MECHANICAL: `_split_flow` honors backslash escapes inside double-quoted strings (skip the char after a backslash), mirroring the fix already applied to `_strip_comment`/`_parse_double_quoted`.
  - [x] PROCESS: `uv run goc validate` is clean and the existing yaml-lite round-trip behavior is unregressed.
worker: {who: "claude[bot]", where: main}
---

# yaml-lite flow collection mis-splits on a backslash-escaped quote

## Location

`goc/_vendor/yaml_lite.py:345-372` — `_split_flow`, reached from
`_parse_flow_mapping` (line 333) and `_parse_flow_sequence` (line 323).

## What's broken

`_split_flow` walks the flow content char-by-char and toggles quote
state on every quote character, with **no backslash-escape awareness**:

```python
for c in text:
    if in_q:
        buf.append(c)
        if c == in_q:          # <-- no check for a preceding backslash
            in_q = None
    elif c in ('"', "'"):
        in_q = c
        buf.append(c)
    ...
    elif c == "," and depth == 0:
        parts.append("".join(buf))
        buf = []
```

The emitter (`goc/engine.py:198` `_yaml_inline` → `_dq`) escapes a
literal double-quote inside an inline-mapping value as `\"`. When that
value is read back, `_split_flow` sees the backslash-escaped `\"` as a
*closing* quote, then treats the next structural `"` as a *reopening*
quote — so the comma separating the next key/element is consumed inside
quote-mode and never splits. The trailing keys/elements are folded into
the first element and lost.

This is the exact backslash-blindness already fixed for the sibling
function `_strip_comment` (closed card
[yaml-lite-strip-comment-defeated-by-unbalanced-quote-in-bare-value](../yaml-lite-strip-comment-defeated-by-unbalanced-quote-in-bare-value/)),
and the dequote functions `_parse_double_quoted`
(`yaml_lite.py:300-307`) handle `\\` escapes correctly. `_split_flow`
(and the structurally-identical `_split_key` at `yaml_lite.py:377`) were
not repaired.

## Empirical evidence

`uv run python deck/<title>/reproduce.py`:

```
--- case 1: worker mapping ---
emitted : 'worker: {who: "a\\"", where: b}'
parsed  : {'who': '"a\\"", where: b'}
expected: {'who': 'a"', 'where': 'b'}

--- case 2: inline flow sequence with escaped quote ---
source  : sample: ["a\"", "b"]
parsed  : ['a"", "b']
expected: ['a"', 'b']

FAIL: worker mapping round-trip corrupted; flow-sequence element with escaped quote mis-split
```

Case 1: the `where` key is lost entirely; the comma and the remainder
of the mapping are folded into the `who` value. Case 2: the two
sequence elements are folded into one — the structural comma after the
escaped quote is swallowed inside quote-mode.

(`emit_frontmatter` only produces flow style for *mappings*, not lists,
so case 2 authors the flow sequence by hand to exercise the same
`_split_flow` path; the defect is in the shared splitter, not in any one
field's emitter.)

## Why it matters

The `worker` field is a documented public frontmatter contract
(AGENTS.md: "a mapping when branch context is known
`worker: {who: rodja, where: feature/foo}`"). A worker/branch identifier
that happens to contain a double-quote silently corrupts the card on the
next emit/parse cycle (any `goc status`, `goc advance`, `goc move`, etc.
that rewrites frontmatter), dropping the `where` and mangling `who`. The
emitter produces the escaped form, so the parser cannot read back what
its own emitter wrote — an asymmetric round-trip bug in the api-contract
surface.

Narrow trigger (the value must contain a double-quote; common names with
balanced quotes like `Jane "JJ" Doe` have even counts and round-trip
fine), hence `contribution: low`.

## Fix

In `_split_flow`, when inside a double-quoted string, skip the character
following a backslash so an escaped `\"` is not seen as a delimiter —
mirroring `_parse_double_quoted`. Sketch:

```python
elif c == "\\" and in_q == '"':
    buf.append(c)
    escaped = True   # consume the next char literally
```

(Single-quoted YAML uses `''` doubling, not backslash escapes, so the
escape handling applies only to the `"` quote state.) Apply the same
guard to `_split_key` (`yaml_lite.py:377`), which has the identical
quote-tracking loop, and add a round-trip regression for both flow
mappings and flow sequences.

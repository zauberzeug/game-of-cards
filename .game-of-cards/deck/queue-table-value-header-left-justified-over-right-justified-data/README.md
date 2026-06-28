---
title: queue-table-value-header-left-justified-over-right-justified-data
status: disproved
stage: null
contribution: low
created: "2026-06-24T14:20:37Z"
closed_at: "2026-06-24T14:24:30Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
summary: "DISPROVED 2026-06-24. The claim that the VALUE column header is left-justified over right-justified data is unobservable: the VALUE data string is bounded at 4 chars (`30.0`), strictly shorter than the 5-char `VALUE` header, so the column width is always pinned to 5 by the header, and at width 5 `_display_ljust` and `_display_rjust` return the identical unpadded `VALUE`. No misalignment occurs in any shipping flow."
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — the VALUE header and its data cells share the same justification (both right-edge-aligned within the column).
  - [ ] TDD: a regression test asserts the VALUE header's right edge lines up with its data cells' right edge in `render_table` (both verbose>=1 and verbose==0 layouts).
  - [ ] MECHANICAL: the header row in `render_table` right-justifies the VALUE header cell to match `_display_rjust` on the VALUE data cells, while every other header stays left-justified.
  - [ ] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green.
---

# queue-table-value-header-left-justified-over-right-justified-data

> ⚠ **Disproved 2026-06-24.** No misalignment occurs in any shipping flow.
> The VALUE data string is bounded at 4 characters (`"30.0"`), strictly
> shorter than the 5-character `"VALUE"` header, so the column width is
> **always** pinned to 5 by the header. At width 5,
> `_display_ljust("VALUE", 5)` and `_display_rjust("VALUE", 5)` return the
> identical unpadded string `"VALUE"` — the header/data justification
> mismatch is unobservable. The right-justified data's right edge already
> lines up under the header's right edge, which is correct right-alignment.

## Location

`goc/engine.py:2757` (header row) versus `:2766` and `:2777` (VALUE data
cells) in `render_table`.

## Hypothesis (rejected)

The header row left-justifies every header (including VALUE) with one blanket
`_display_ljust` comprehension:

```python
out_lines.append("  ".join(_display_ljust(h, widths[i]) for i, h in enumerate(headers)))
```

while the VALUE column is the only column whose data is right-justified
(`_display_rjust`, lines 2766 / 2777). The hypothesis was that this asymmetry
shifts the right-justified value digits out from under their left-justified
`"VALUE"` label on every render.

## Why it's disproved

The asymmetry in the source is real, but it produces **no observable
misalignment** because the value-string width can never exceed the header
width:

- `_format_value` emits `f"{v:.1f}"`, and `compute_values` bounds the GRPW
  value at `max_rank/(1-γ) = 3/(1-0.9) = 30.0`. The widest reachable value
  string is `"30.0"` — 4 characters.
- The header `"VALUE"` is 5 characters. So
  `widths[VALUE] = max(5, ≤4) = 5` on every render: the column width is
  always pinned to the header length.
- At a width equal to its own length, the header has no padding to place:
  `_display_ljust("VALUE", 5) == _display_rjust("VALUE", 5) == "VALUE"`.
  The ljust/rjust choice for the header is a no-op.
- The right-justified data (`"  9.0"`, `" 30.0"`) therefore lands with its
  right edge flush under the header's right edge — the correct, intended
  rendering for a right-aligned numeric column.

The justification mismatch only becomes visible for a value string of
**6+ characters** (e.g. `"1234.5"`), which forces the column wider than the
header and leaves the left-justified header trailing a pad space. That input
is **unreachable**: `compute_values` is the only producer of the `values`
dict in shipping code and it can never emit a value ≥ 1000. No card-authoring
path, no CLI flag, and no consumer flow feeds an out-of-bound value into
`render_table`, so the offending column geometry never arises.

Per the audit reachability rule, a defect with no input path that produces
the offending shape in shipping code is theoretical, not real.

## Empirical evidence

`uv run python deck/<title>/reproduce.py` (run against current `main`):

```
value=9.0 verbose=0: header='VALUE' data='  9.0' aligned=True
value=9.0 verbose=1: header='VALUE' data='  9.0' aligned=True
value=30.0 verbose=0: header='VALUE' data=' 30.0' aligned=True
value=30.0 verbose=1: header='VALUE' data=' 30.0' aligned=True
PASS: for every reachable value the VALUE header and data share their right edge
```

For the only reachable values (`9.0`, `30.0`) the header and data share their
right edge. The misalignment would surface only for an out-of-bound 6-char
value (e.g. `"1234.5"`, width 6) that forces the column wider than the header
and leaves the left-justified header trailing a pad space — but
`compute_values` can never emit such a value, so that geometry never arises.

## Re-promotion condition

Re-open only if the GRPW value bound is ever raised above `999.95` (so value
strings can reach 6+ characters and exceed the `"VALUE"` header width), or if
a new `render_table` caller is added that feeds a `values` dict not produced
by `compute_values`. At that point right-justifying the VALUE header to match
its data becomes a real fix. Until then there is no observable defect.

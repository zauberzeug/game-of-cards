---
title: queue-table-misaligns-when-a-cell-contains-a-wide-character
summary: "`render_table` (engine.py:2689-2715), the default `goc` queue view, computes column widths with `len()` and pads with `str.ljust()`/`str.rjust()` — both codepoint-based — so a cell holding an East-Asian wide character (two terminal columns) skews every column to its right. `render_board` was fixed for exactly this via `_display_width`/`_display_ljust` (closed card board-grid-misaligns-when-a-row-contains-the-wide-hourglass-glyph); the table renderer was left on the codepoint path. Low contribution: goc emits no wide glyph into table cells itself, so the trigger is a user-authored wide title/tag, which the repo's card-authoring rules already discourage."
status: done
stage: null
contribution: low
created: "2026-06-22T19:51:28Z"
closed_at: "2026-06-22T20:11:17Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — the title column ends at the same display column on a wide-glyph row as on an ASCII row.
  - [x] TDD: a regression test asserts `render_table` and `render_board` agree on inter-column display alignment for a row containing a wide character.
  - [x] MECHANICAL: `render_table` measures and pads with `_display_width`/`_display_ljust` (and a display-aware right-justify for the VALUE column) rather than `len()`/`str.ljust()`/`str.rjust()`, mirroring `render_board`.
  - [x] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green.
worker: {who: "claude[bot]", where: main}
---

# queue-table-misaligns-when-a-cell-contains-a-wide-character

## Location

`goc/engine.py:2689` (width computation) and `:2691`, `:2696`-`:2715` (header
and cell padding) in `render_table`.

> Resolved 2026-06-22: `render_table` now sizes and pads by display width
> (`_display_width` / `_display_ljust` / the new `_display_rjust`), mirroring
> `render_board`. The wide-glyph queue grid is aligned.

## What was broken

`render_table` is the default `goc` queue view. It sized every column by
codepoint count and padded with codepoint-based justification:

```python
widths = [max(len(h), max((len(r[i]) for r in rows), default=0)) for i, h in enumerate(headers)]
out_lines.append("  ".join(h.ljust(widths[i]) for i, h in enumerate(headers)))
...
cells = [
    r[0].ljust(widths[0]),
    _wrap(r[1].ljust(widths[1]), t.status, enabled),
    ...
```

`len("日本語-title")` is 9, but the string occupies 12 terminal columns (each
CJK glyph is double-width). `str.ljust` padded to a codepoint count, not a
display width, so any row whose title (or tags) contained a wide character
pushed every following column out of alignment.

`render_board`, by contrast, was switched to display-width-aware helpers
`_display_width` and `_display_ljust` when the closed card
[board-grid-misaligns-when-a-row-contains-the-wide-hourglass-glyph](../board-grid-misaligns-when-a-row-contains-the-wide-hourglass-glyph/)
landed. The same fix had never been applied one renderer over.

## Empirical evidence

`uv run python deck/<title>/reproduce.py` (the harness measures where the
second column begins — the title text's own end is the wrong invariant, since
the widest title fills its column with zero trailing pad). After the fix:

```
TABLE rows:
  日本語-title  open    medium    3.0  none        0/1
  ascii-title   open    medium    3.0  none        0/1
  STATUS column starts at display col: wide-row=14  ascii-row=14

no defect (columns aligned)
```

Before the fix the codepoint path put the STATUS column at display col 16 on
the wide-glyph row vs 13 on the ASCII row — a 3-column skew.

## Why it matters

`render_table` is the view every user and agent sees most (`goc` with no
flags). Card titles and tags are free-form strings: `goc new` does not enforce
ASCII and `goc validate` does not reject non-ASCII titles — non-ASCII is only
an advisory flagged by `_check_title_antipatterns` during the optional
`quality-pass`. So an internationalized or emoji-bearing title renders a
visibly skewed queue grid.

Reachability and severity are bounded, hence **low** contribution: unlike the
board's `⏳` hourglass — a wide glyph the tool *itself* emits, which made the
board card higher-impact — `render_table` emits no wide glyph into any cell
on its own. The only trigger is a user-authored wide title/tag, and the
repo's own card-authoring rules already discourage non-ASCII titles. The card
is filed to close the derivation gap (board fixed, table not), not because the
misalignment is commonly hit.

## Fix (applied)

Mirrored `render_board`: the width computation now uses `_display_width(...)`,
and every `.ljust(widths[i])` / `.rjust(widths[i])` in the header and cell
padding is now `_display_ljust(...)` / `_display_rjust(...)`. A new
`_display_rjust` helper (sibling of `_display_ljust`) provides the
display-aware right-justify for the VALUE column. A regression test in
`tests/test_board.py` asserts the table's STATUS column aligns across a
wide-glyph row and that both renderers keep every row at one display width.


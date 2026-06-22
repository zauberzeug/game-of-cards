---
title: queue-table-misaligns-when-a-cell-contains-a-wide-character
summary: "`render_table` (engine.py:2689-2715), the default `goc` queue view, computes column widths with `len()` and pads with `str.ljust()`/`str.rjust()` — both codepoint-based — so a cell holding an East-Asian wide character (two terminal columns) skews every column to its right. `render_board` was fixed for exactly this via `_display_width`/`_display_ljust` (closed card board-grid-misaligns-when-a-row-contains-the-wide-hourglass-glyph); the table renderer was left on the codepoint path. Low contribution: goc emits no wide glyph into table cells itself, so the trigger is a user-authored wide title/tag, which the repo's card-authoring rules already discourage."
status: active
stage: null
contribution: low
created: "2026-06-22T19:51:28Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — the title column ends at the same display column on a wide-glyph row as on an ASCII row.
  - [ ] TDD: a regression test asserts `render_table` and `render_board` agree on inter-column display alignment for a row containing a wide character.
  - [ ] MECHANICAL: `render_table` measures and pads with `_display_width`/`_display_ljust` (and a display-aware right-justify for the VALUE column) rather than `len()`/`str.ljust()`/`str.rjust()`, mirroring `render_board`.
  - [ ] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green.
worker: {who: "claude[bot]", where: main}
---

# queue-table-misaligns-when-a-cell-contains-a-wide-character

## Location

`goc/engine.py:2689` (width computation) and `:2691`, `:2696`-`:2715` (header
and cell padding) in `render_table`.

## What's broken

`render_table` is the default `goc` queue view. It sizes every column by
codepoint count and pads with codepoint-based justification:

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
CJK glyph is double-width). `str.ljust` pads to a codepoint count, not a
display width, so any row whose title (or tags) contains a wide character
pushes every following column out of alignment.

`render_board`, by contrast, was switched to display-width-aware helpers
`_display_width` (engine.py:2825) and `_display_ljust` (engine.py:2834) when
the closed card
[board-grid-misaligns-when-a-row-contains-the-wide-hourglass-glyph](../board-grid-misaligns-when-a-row-contains-the-wide-hourglass-glyph/)
landed. The same fix was never applied one renderer over.

## Empirical evidence

`uv run python deck/<title>/reproduce.py`:

```
TABLE rows:
  日本語-title    open    medium    3.0  none        0/1
  ascii-title  open    medium    3.0  none        0/1
  title-cell display width: wide-row=12  ascii-row=11

DEFECT REPRODUCED: title column ends at display col 12 on the wide-glyph row vs 11 on the ASCII row — the grid is skewed by 1 columns.
```

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

## Fix (proposed — do not apply here)

Mirror `render_board`: replace `len(...)` at `:2689` with `_display_width(...)`,
and replace each `.ljust(widths[i])` / `.rjust(widths[i])` at `:2691` and
`:2696`-`:2715` with `_display_ljust(...)` and a display-aware right-justify
for the VALUE column. Add a regression test asserting the table and board
agree on the separator's display column for a wide-glyph row.


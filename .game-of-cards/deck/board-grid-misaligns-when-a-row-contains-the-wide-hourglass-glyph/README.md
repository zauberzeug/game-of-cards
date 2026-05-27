---
title: board-grid-misaligns-when-a-row-contains-the-wide-hourglass-glyph
summary: "`goc --board` computes column widths with `len()`, which counts the impediment marker `⏳` (U+23F3, East-Asian-width Wide) as 1 codepoint though terminals render it 2 columns wide. Every row bearing the marker is shifted one display column right of the header, skewing the grid. UNVERIFIED: hunter measured the offset but no reproduce.py written yet."
status: done
stage: null
contribution: medium
created: "2026-05-27T09:50:39Z"
closed_at: 2026-05-27T10:02:02Z
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: a reproduce.py builds a board column with one `⏳`-bearing row and one plain row, and asserts the first `|` separator lands at the same display column on both (currently off by one).
  - [x] TDD: rows without the marker remain aligned (no regression).
  - [x] MECHANICAL: column width + cell padding use a display-width measure (East-Asian-width aware) instead of `len()` for the marked cells.
worker: {who: "claude[bot]", where: main}
---

# board grid misaligns when a row contains the wide `⏳` glyph

> VERIFIED (2026-05-27) — `reproduce.py` renders a board with one
> impeded (`⏳`-bearing) row and one plain row and confirmed the marked
> row's first `|` separator landed at display column 22 vs 21 for the
> header/unmarked rows. The fix (display-width-aware padding) aligns all
> three at column 21. `unverified` tag dropped.

## Location

`goc/engine.py:2217` (marker append) and `goc/engine.py:2227` (column width):

```python
marker += " ⏳"
...
max(20, len(c.upper()), max((len(cell) for cell in rendered_by_status[c]), default=0))
```

## Hypothesis (what's broken)

The board column width and the per-cell right-padding are computed with
`len()`, which counts codepoints. The impediment marker `⏳` (U+23F3) has
East-Asian-width property **Wide (W)**: `len('⏳') == 1`, but a terminal renders
it across **2** display columns. So a cell containing the marker is padded as if
it occupies one fewer column than it visually does, and that row's trailing
`|` separator (and everything after it) is shifted one display column right of
the header row and of unmarked rows. The grid skews for any row whose card is
dependency-blocked or carries an active `waiting_on` impediment — a common
state.

This is distinct from the already-filed board cards:
[`board-marks-pullable-and-impeded-cards-with-the-same-hourglass-glyph`](../board-marks-pullable-and-impeded-cards-with-the-same-hourglass-glyph/)
(glyph *ambiguity*, two states share one glyph) and
[`board-active-card-worker-label-not-truncated`](../board-active-card-worker-label-not-truncated/)
(label *truncation*). Neither addresses display-width miscounting of wide
glyphs.

## Empirical evidence (hunter measurement, not yet a reproduce.py)

Hunter rendered a 2-card open column and measured display columns: the header
`|` and the unmarked row's `|` land at display column 25, but the `⏳`-bearing
row's `|` lands at display column 26 — one column off.

## Why deferred

Cosmetic-but-real: the board is a primary human-facing surface and the skew is
visible whenever any card is impeded. Parked unverified (not dropped) because
the headline confirmed defect this round is the install data-loss card, and
this candidate still needs an independent reproduce.py plus a fix-approach
decision (vendor a tiny East-Asian-width table vs. add a `wcwidth` dependency —
the project currently has no third-party runtime deps, so a dependency add is a
real decision).

**Decision resolved (2026-05-27):** neither — Python's stdlib
`unicodedata.east_asian_width` classifies `⏳` (and any other glyph) as
Wide/Fullwidth with zero third-party deps and no vendored table to
maintain. `render_board` now measures display width via
`_display_width` and pads via `_display_ljust` instead of `len()` /
`str.ljust()`.

## Falsification recipe

Write `reproduce.py` that renders a board with one impeded and one non-impeded
card in the same column, finds the first `|` on each rendered row, and compares
their display-column positions (computing display width with an East-Asian-width
table). If they already align, the hypothesis is falsified.

## Surfaced by

audit-deck hunter (general-purpose agent), 2026-05-27.

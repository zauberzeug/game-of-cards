# Log

## 2026-06-24 — filed and disproved in one audit session

Surfaced by an audit hunter as a candidate misalignment: `render_table`'s
header row left-justifies the VALUE header (blanket `_display_ljust`,
`engine.py:2757`) while the VALUE data cells are right-justified
(`_display_rjust`, `:2766`/`:2777`).

Read the cited code and reproduced. The asymmetry is real in source but
produces **no observable misalignment**: `_format_value` emits at most
`"30.0"` (4 chars, the `compute_values` bound `max_rank/(1-γ)=30.0`), which is
shorter than the 5-char `"VALUE"` header, so the column width is always pinned
to 5 by the header. At width 5 the header has no padding to place —
`_display_ljust("VALUE", 5) == _display_rjust("VALUE", 5) == "VALUE"` — and the
right-justified data lands flush under the header's right edge, which is the
correct rendering for a right-aligned numeric column.

The mismatch would only surface for a 6+-char value string (≥ 1000), which
`compute_values` (the only producer of the `values` dict in shipping code)
never emits. With no reachability path, the defect is theoretical, not real →
disproved. `reproduce.py` exits zero, demonstrating alignment holds for every
reachable value.

Re-promotion condition recorded in README: re-open only if the GRPW value
bound is raised above `999.95`, or a new `render_table` caller feeds a
`values` dict not produced by `compute_values`.

Distinct from the closed card
`queue-table-misaligns-when-a-cell-contains-a-wide-character`, which fixed
display-width *measurement* and added `_display_rjust` for the VALUE data —
this candidate concerned the header-row justification, which that card left on
`_display_ljust` (correctly, as shown above).

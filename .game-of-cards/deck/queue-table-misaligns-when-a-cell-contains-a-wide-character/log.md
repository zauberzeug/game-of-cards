## 2026-06-22T20:30:00Z — Closure

- **What changed**: `goc/engine.py` — `render_table` now sizes columns with
  `_display_width` and pads with `_display_ljust` / the new `_display_rjust`
  (VALUE column), mirroring `render_board`. Added `_display_rjust` helper as
  the display-aware sibling of `_display_ljust`.
- **Reproduce harness correction**: `reproduce.py` previously measured where
  the title *text* ends — the wrong invariant, since the widest title fills
  its column with zero trailing pad, so two titles of different display widths
  always differ regardless of alignment. Rewrote `first_gap_col` →
  `second_col_start`, which measures the display column where the STATUS
  column begins. Verified it reproduces on the unfixed codepoint path
  (16 vs 13) and passes on the fixed path (14 vs 14).
- **Verification**: `reproduce.py` exits 0 (STATUS column at display col 14 on
  both the wide-glyph and ASCII rows). New regression test
  `test_table_aligns_columns_for_wide_character_row` asserts the table's
  STATUS column aligns across a wide-glyph row and that both `render_table`
  and `render_board` keep every row at a single display width.
- **Audit**: PASS — no principle touched, mechanical fix (display-width
  parity between the two renderers; closes a derivation gap left by
  board-grid-misaligns-when-a-row-contains-the-wide-hourglass-glyph).
- **Project impact**: n/a
- **Tests**: 529 passed / 0 failed (full `unittest discover -s tests`);
  `goc validate` clean; plugin mirrors synced (engine.py).

## Closure verification (2026-06-22T20:11:14Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-06-22 — Closure' present

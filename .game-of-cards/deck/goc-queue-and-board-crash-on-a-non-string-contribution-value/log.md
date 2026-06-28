# Log

## 2026-06-21 — Closure (filed and fixed, fix-through)

Surfaced during an empty-queue audit pass. The `Card.contribution`
property returned the raw frontmatter value with no coercion, so a card
with a non-string scalar `contribution` (e.g. `42` from a hand edit or a
legacy card) crashed both read-only views before validation could run:
`render_table` on `len()`/`.ljust()` and `render_board` on `c[0]`.

This refutes the closed sibling
`board-crashes-when-a-card-has-no-contribution-value`, whose summary
asserts the table renderer "survives because it does not index" — true
only for the empty/None shape; the non-string scalar shape crashes the
table on `len()` and still crashes the board's empty-guard on `c[0]`.

Fix: coerce non-None values to `str` in the property, keeping None
falsy (`return "" if v is None else str(v)`) so the sibling's empty-case
`[?]` board marker does not regress to `[N]`. One source line in
`goc/engine.py`. `compute_values` was already safe (it uses
`.get(..., default)` on the contribution key).

Regression coverage: `tests/test_board.py` gains
`test_renderers_tolerate_non_string_contribution` (both renderers + the
`[4]` marker) and `test_board_marks_none_contribution_with_placeholder`
(None still yields `[?]`, never `[N]`). reproduce.py exits 0 after the
fix and 1 before. Plugin mirrors synced byte-for-byte; full regression
suite and `goc validate` clean.

## Closure verification (2026-06-21T19:00:56Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [ ] log-md-closure-entry FAIL — no '## 2026-06-21 — Closure' section

## Closure verification (2026-06-21T19:01:08Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-06-21 — Closure' present

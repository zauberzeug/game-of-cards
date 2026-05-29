## 2026-05-29T05:17:30Z — Closure

- **What changed**: `goc/engine.py:1303-1306` `find_half_edges` — wrap `inverse_list = other.frontmatter.get(inverse) or []` with the same `isinstance(..., list)` guard the outer walker already applies, so a hand-edited bare-string inverse is treated as an empty edge set instead of falling back to Python's substring `in`.
- **Verification**: reproduce.py exits 0 (was: empty list, now: 1 half-edge `acard: advances contains 'bcard' but bcard.advanced_by is missing 'acard'`). New regression tests in `tests/test_non_list_advances_guard.py` (substring-match case + exact-match bare-string case) pass.
- **Audit**: no rubric configured; mechanical fix — sibling inner-walker of the `compute-values-iterates-non-list-advances-character-by-character` family (same root cause: missing list-isinstance guard on a walker downstream of `validate_card`).
- **Project impact**: n/a
- **Tests**: 184 passed / 0 failed / 0 xfailed (full `python -m unittest discover -s tests` suite, including 2 new regression cases).
- **Bundled with**: none

## Closure verification (2026-05-29T05:17:42Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-05-29 — Closure' present

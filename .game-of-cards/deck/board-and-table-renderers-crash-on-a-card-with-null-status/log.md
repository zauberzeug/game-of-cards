## 2026-06-26T02:15:00Z — Closure

- **What changed**: `goc/engine.py:735-743` — `Card.status` now coerces a
  `None`/non-string frontmatter value to a string (`"" if v is None else
  str(v)`), mirroring the existing `Card.contribution` guard. Fixes both
  `render_table` (`_display_width(None)`) and `render_board` (`None.upper()`)
  crashing the whole deck view on one card with `status: null`.
- **Verification**: reproduce.py exits 0 post-fix (`Card.status == ''`, both
  renderers OK); was exit 1 pre-fix (both crashed). New regression test
  `test_renderers_tolerate_null_status` in `tests/test_board.py`.
- **Audit**: PASS — no principle touched, mechanical fix (None/non-string
  coercion at a property boundary; sibling of the non-string-contribution fix).
- **Project impact**: n/a
- **Tests**: 603 passed / 0 failed (plugin mirrors re-synced after the
  engine.py edit).
- **Bundled with**: n/a

## Closure verification (2026-06-26T02:10:25Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-06-26 — Closure' present

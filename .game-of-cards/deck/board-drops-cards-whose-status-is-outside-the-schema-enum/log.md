## 2026-06-25T20:31:21Z — Closure

- **What changed**: `goc/engine.py` `render_board` — a pre-pass appends any status present in `cards` but absent from `schema.status_values` as a trailing column (first-seen order), then the filing loop files every card unconditionally. The board now mirrors `render_table`'s show-everything contract instead of silently dropping off-enum statuses.
- **Verification**: `reproduce.py` exits 0 (was 1); `legacy-blocked` now renders under a trailing `BLOCKED` column. New regression `tests/test_board.py::test_board_surfaces_card_with_status_outside_schema_enum` passes.
- **Audit**: PASS — no principle touched, mechanical fix (a read view aligning with its sibling renderer; `goc validate` remains the channel that flags an off-enum status).
- **Project impact**: n/a
- **Tests**: 600 passed / 0 failed (full `unittest discover -s tests` green); `goc validate` exit 0 after plugin-mirror sync.
- **Bundled with**: n/a

## Closure verification (2026-06-25T20:31:32Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-06-25 — Closure' present

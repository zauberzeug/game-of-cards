# Log — board-crashes-when-a-card-has-no-contribution-value

## 2026-05-27T00:00:00Z — Closure

- **What changed**: `goc/engine.py:2209-2210` (`card_cell` in `render_board`) — guard the `contribution[0]` index so an empty/None value degrades to a `[?]` placeholder instead of crashing the whole board.
- **Verification**: reproduce.py exits 0; both `blank (None)` and `absent ("")` variants now render OK. `goc --board` renders clean.
- **Audit**: PASS — no principle touched, mechanical fix (bounds guard mirroring the table renderer's existing tolerance).
- **Project impact**: n/a
- **Tests**: no pytest suite; `goc validate` clean, plugin mirrors synced.
- **Bundled with**: n/a

## Closure verification (2026-05-27T06:15:52Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present

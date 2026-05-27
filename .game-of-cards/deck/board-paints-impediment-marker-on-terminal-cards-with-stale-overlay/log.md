
## 2026-05-27T09:30:00Z — Closure

- **What changed**: `goc/engine.py` `card_cell` in `render_board` — gated the whole `not_ready` predicate on `t.status not in TERMINAL_STATUSES`, so the ⏳ impediment glyph no longer fires on done/disproved/superseded cards that retain a stale `waiting_on` overlay. Stored overlay fields are NOT mutated on close (preserved as historical record).
- **Verification**: reproduce.py exits 1 (was 0); all three terminal cards now render without ⏳.
- **Audit**: PASS — no principle touched, mechanical fix (renderer predicate divergence; the board now matches `card_is_ready`'s status guard).
- **Project impact**: n/a
- **Tests**: no pytest suite; `goc validate` clean.
- **Bundled with**: none

## Closure verification (2026-05-27T08:21:27Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present

## 2026-05-27T00:00:00Z — Closure

- **What changed**: `goc/engine.py` `card_cell` in `render_board` — emit shared ⏳ glyph when a card is dependency-blocked OR `waiting_impedes(t)`; deck skill `goc --board` legend row documents the glyph.
- **Verification**: reproduce.py exits 0; impeded card now renders `[h] ⏳`, plain card `[h]`.
- **Audit**: PASS — no principle touched, mechanical fix (renderer/predicate divergence; the board now matches the `card_is_ready` queue guard).
- **Project impact**: n/a
- **Tests**: no pytest suite; `goc validate` clean; plugin mirrors synced; openclaw port `--check` clean.
- **Bundled with**: none

## Closure verification (2026-05-27T07:45:02Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present

## 2026-05-27 — Later evidence: follow-on gap

- The impediment term added to `card_cell` here did not inherit the
  adjacent dependency-block term's `status == "open"` gate, so terminal
  (done/disproved/superseded) cards retaining a stale `waiting_on`
  overlay were painted ⏳. Fixed in
  [board-paints-impediment-marker-on-terminal-cards-with-stale-overlay](../board-paints-impediment-marker-on-terminal-cards-with-stale-overlay/)
  by gating the whole `not_ready` predicate on `status not in TERMINAL_STATUSES`.

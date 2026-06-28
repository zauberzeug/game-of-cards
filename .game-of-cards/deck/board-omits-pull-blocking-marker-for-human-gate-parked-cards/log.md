## 2026-06-06T05:30:00Z — Closure

- **What changed**: `goc/engine.py:2668` — the board's `not_ready` predicate gained the `t.human_gate != "none"` axis so a human-gate-parked open card now carries the ⏳ not-pullable marker, coupling the board to `card_is_ready` / `card_is_workable_for_scheduler`. Plugin mirrors (claude/codex/openclaw `goc/engine.py`) re-synced.
- **Verification**: `reproduce.py` exits 0 after the fix (`gated-decision [m] ⏳`); was exit 1 before. New regression `tests/test_board.py::test_board_marks_human_gate_parked_card_not_pullable` asserts the gated card carries ⏳ while the free card does not and the impeded card keeps its ⏳.
- **Audit**: PASS — no principle touched, mechanical fix (predicate-coupling correction in a renderer; reuses the existing ⏳ marker exactly as the closed `board-omits-marker-for-cards-with-active-waiting-overlay` sibling did).
- **Project impact**: n/a
- **Tests**: 395 passed / 0 failed (full suite); `goc validate` clean; `python scripts/sync_plugin_assets.py --check` green.
- **Bundled with**: (none)

Filed and fixed-through in one pull-card session (queue was empty of
ready cards; this defect was surfaced by the audit-deck engine-renderer
hunter and cleared the fix-through bar: gate-free, single-site,
in loaded context).

## Closure verification (2026-06-06T05:10:18Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-06-06 — Closure' present

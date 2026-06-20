## 2026-06-20T05:08:00Z — Closure

- **What changed**: `goc/templates/hooks/deck_session_start.py` — added
  `_NULL_SET` + `_scalar_or_none` and routed `_card_waiting_on` /
  `_card_waiting_until` through it, so explicit YAML null literals
  (`null`, `Null`, `NULL`, `~`) resolve to `None` and stop being read as a
  live impediment. Mirrors `yaml_lite._NULL_SET`, matching the engine.
- **Verification**: reproduce.py exits 0 — all 5 explicit-null cases now
  agree with `engine.waiting_impedes` (hook=False engine=False); canonical
  `external` control still impedes.
- **Audit**: PASS — mechanical fix; restores the documented invariant that
  `_is_impeded` mirrors `goc.engine.waiting_impedes`. No principle redefined.
- **Project impact**: n/a
- **Tests**: 469 passed / 0 failed (full `unittest discover -s tests`);
  plugin-mirror parity re-synced (5 mirror files).
- **Bundled with**: none

## Closure verification (2026-06-20T05:08:21Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-06-20 — Closure' present

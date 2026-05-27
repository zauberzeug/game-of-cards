## 2026-05-27T00:00:00Z — Closure

- **What changed**: `goc/engine.py` `render_json` — added `waiting_on` and `waiting_until` keys to the record dict, alongside `human_gate`, mirroring `worker` / relationship-edge emission. Plugin mirrors (claude/codex/openclaw) auto-synced.
- **Verification**: reproduce.py exits 0; JSON record now contains both keys. New `tests/test_json_overlay.py` pins active-overlay values and null-when-absent symmetry.
- **Audit**: PASS — no principle touched, mechanical fix (field-symmetric serialization of an existing schema field).
- **Project impact**: n/a
- **Tests**: 167 passed / 0 failed

## Closure verification (2026-05-27T11:56:41Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present

## 2026-06-24T19:30:00Z — Closure

- **What changed**: `goc/engine.py` — added `_value_path_slugs` helper that strips the trailing `"self"` / `"cycle"` terminator; `render_json` now emits `_value_path_slugs(...)` for `value_path` (engine.py:2864) and `_format_why` routes its existing trailing-strip through the same helper. Engine mirrors re-synced to the three plugin payloads.
- **Verification**: reproduce.py exits 0 — `root-card` value_path `['mid-card','leaf-card']` (was `[...,'self']`), leaf `[]` (was `['self']`); new `tests/test_json_value_path_sentinels.py` (3 tests) green.
- **Audit**: PASS — no principle touched, mechanical fix (machine surface made to agree with the already-pinned `_format_why` contract from the two closed `why-trace-renders-spurious-*-hop` cards).
- **Project impact**: n/a
- **Tests**: 581 passed / 0 failed / 0 xfailed

## Closure verification (2026-06-24T19:25:01Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-06-24 — Closure' present

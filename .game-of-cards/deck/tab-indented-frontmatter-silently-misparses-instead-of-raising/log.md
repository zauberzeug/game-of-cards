## 2026-06-15T06:05:00Z — Closure

- **What changed**: `goc/_vendor/yaml_lite.py:75` (`_peek`) — added a tab guard at the one structural chokepoint, so tab-indented mapping keys / sequence items / mixed-indent lines raise `ParseError` per the docstring contract, while block-scalar content (read directly, not via `_peek`) keeps its tabs.
- **Verification**: reproduce.py exits 0 (all 3 cases now raise); 5 new regression tests in `tests/test_yaml_lite.py` pass.
- **Audit**: PASS — no principle touched, mechanical fix (align code to its own documented contract).
- **Project impact**: n/a
- **Tests**: 451 passed / 0 failed (full suite); `goc validate` clean (exit 0).
- **Bundled with**: n/a

## Closure verification (2026-06-15T05:50:52Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-06-15 — Closure' present

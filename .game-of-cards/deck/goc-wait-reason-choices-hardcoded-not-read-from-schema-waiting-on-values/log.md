## 2026-05-30T09:50:20Z — Closure

- **What changed**: `goc/engine.py:2662` — `p_wait --reason` now reads `choices=schema.waiting_on_values` instead of the hardcoded `["external", "resource", "deferred"]` list, matching the adjacent pattern at `engine.py:2643-2645`.
- **Verification**: `tests/test_wait_reason_schema_sourced.py` (new) asserts the argparse choices equal `schema.waiting_on_values`; full regression suite 264/264 pass; `uv run goc validate` clean.
- **Audit**: PASS — no rubric configured; mechanical fix (single-source-of-truth alignment).
- **Project impact**: n/a
- **Tests**: 264 passed / 0 failed / 0 xfailed
- **Bundled with**: none

## Closure verification (2026-05-30T09:50:42Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-05-30 — Closure' present

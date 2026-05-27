## 2026-05-27T03:51:25Z — Closure

- **What changed**: `goc/engine.py` `_format_why` — strip a trailing `"self"` sentinel before the slug loop (recommended approach 1; no value-graph shape change).
- **Verification**: reproduce.py exits 0; `uv run goc -v` prints 0 `self (?)` hops across the queue.
- **Audit**: PASS — no principle touched, mechanical fix (display-contract correction).
- **Project impact**: n/a
- **Tests**: no pytest suite; reproduce.py 1 passed; goc validate clean; plugin sync --check green.

## Closure verification (2026-05-27T03:51:28Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present

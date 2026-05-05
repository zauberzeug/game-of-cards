## 2026-05-04 — Closure

- **What changed**: goc/engine.py — read-only status filters now use the explicit lifecycle status enum plus `all`.
- **Verification**: `uv run python deck/invalid-status-filter-silently-empties-queue/reproduce.py` -> exit 0; `uv run pytest` -> 28 passed; `uv run goc validate --quiet` -> exit 0.
- **Audit**: PASS — no rubric configured; mechanical fix
- **Project impact**: typoed queue status filters now fail visibly instead of returning misleading empty queues.
- **Tests**: 28 passed / 0 failed / 0 xfailed
- **Bundled with**: n/a

## Closure verification (2026-05-04)

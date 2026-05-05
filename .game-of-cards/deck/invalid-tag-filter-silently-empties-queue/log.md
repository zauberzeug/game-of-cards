## 2026-05-04 — Closure

- **What changed**: goc/engine.py — read-only tag filters now validate against canonical tags, including project-local tag extensions.
- **Verification**: `uv run python deck/invalid-tag-filter-silently-empties-queue/reproduce.py` -> exit 0; `uv run pytest` -> 30 passed; `uv run goc validate --quiet` -> exit 0.
- **Audit**: PASS — no rubric configured; mechanical fix
- **Project impact**: typoed tag filters now fail visibly instead of returning misleading empty queues.
- **Tests**: 30 passed / 0 failed / 0 xfailed
- **Bundled with**: n/a

## Closure verification (2026-05-04)

## 2026-05-04 — Closure

- **What changed**: goc/engine.py — `--since` now validates `YYYY-MM-DD` input at the Click boundary before done-card filtering.
- **Verification**: `uv run python deck/invalid-since-date-silently-empties-done-query/reproduce.py` -> exit 0; `uv run pytest` -> 26 passed; `uv run goc validate --quiet` -> exit 0.
- **Audit**: PASS — no rubric configured; mechanical fix
- **Project impact**: typoed done-card date filters now fail visibly instead of returning misleading empty results.
- **Tests**: 26 passed / 0 failed / 0 xfailed
- **Bundled with**: n/a

## Closure verification (2026-05-04)

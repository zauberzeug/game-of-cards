## 2026-05-04 — Closure

- **What changed**: goc/engine.py — `--max-rows` now uses Click integer range validation with a minimum of 0.
- **Verification**: `uv run python deck/negative-board-row-limit-hides-cards/reproduce.py` -> exit 0; `uv run pytest` -> 24 passed; `uv run goc validate --quiet` -> exit 0.
- **Audit**: PASS — no rubric configured; mechanical fix
- **Project impact**: board row caps can no longer hide cards through negative Python slice semantics.
- **Tests**: 24 passed / 0 failed / 0 xfailed
- **Bundled with**: n/a

## Closure verification (2026-05-04)

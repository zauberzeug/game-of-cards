## 2026-05-04 — Closure

- **What changed**: goc/engine.py — the kanban board renderer now includes the valid `superseded` status as its own column.
- **Verification**: `uv run python deck/superseded-cards-hidden-from-board/reproduce.py` -> exit 0; `uv run pytest` -> 23 passed; `uv run goc validate --quiet` -> exit 0.
- **Audit**: PASS — no rubric configured; mechanical fix
- **Project impact**: full-board views no longer hide superseded cards.
- **Tests**: 23 passed / 0 failed / 0 xfailed
- **Bundled with**: n/a

## Closure verification (2026-05-04)

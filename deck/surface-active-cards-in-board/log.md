## 2026-05-04 — Closure

- **What changed**: `goc/engine.py` — default `goc --board` now renders the full deck so ACTIVE is populated, and open queue views prepend a concise active-card notice. Agent guidance in `AGENTS.md`, installed skills, and skill templates now checks `goc --status active` before recommending or claiming work.
- **Verification**: `uv run pytest` -> 10 passed; `uv run goc validate --quiet` -> exit 0; smoke commands showed `surface-active-cards-in-board` in `uv run goc --board --no-color` ACTIVE, in `uv run goc --status active --no-color`, and in the default/open queue active notice. `uv run goc --status all --no-color` labels active/open statuses in one table.
- **Audit**: PASS — no rubric configured; mechanical fix.
- **Project impact**: parallel agents now see claimed work in the natural board/default queue paths before pulling another card.
- **Tests**: 10 passed / 0 failed / 0 xfailed.
- **Bundled with**: n/a.

## Closure verification (2026-05-04)

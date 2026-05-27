# Log


## 2026-05-27T03:40:17Z — Closure

- **What changed**: `goc/engine.py` — added `_waiting_until_instant` (parse
  `waiting_until` to a UTC instant; bare date → midnight UTC, datetime honored
  at full precision, malformed → None) and `_now_instant` (resolve the
  comparison instant: live clock / datetime / legacy `date` hook as midnight).
  `waiting_impedes` and `validate_waiting_overlay` now compare `until_dt > now`
  instead of truncating to a civil date.
- **Verification**: reproduce.py exits 0 (end-of-day `2026-05-27T23:59:59Z`
  still impedes during 2026-05-27 and is not flagged WAITING_OVERDUE early; a
  genuinely-elapsed datetime still surfaces). All four closed sibling
  reproduce scripts still pass (bare-date / malformed-prefix / open-ended /
  UTC-base semantics unchanged).
- **Audit**: PASS — no project rubric configured; honoring the accepted input
  precision (datetime) at read time rather than silently rounding it away.
- **Project impact**: n/a
- **Tests**: 159 passed / 0 failed (full `uv run pytest`); `uv run goc validate`
  clean; `python scripts/sync_plugin_assets.py --check` green (3 mirrors synced).

## Closure verification (2026-05-27T03:40:30Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present

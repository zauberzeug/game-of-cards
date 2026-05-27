## 2026-05-27T00:00:00Z — Closure

- **What changed**: `goc/engine.py` — added `_utc_today()` (returns `datetime.now(tz=timezone.utc).date()`) next to `_utc_now_iso()`; the three read-time guards now default `today` to it instead of `date.today()`: `waiting_impedes`, `validate_waiting_overlay`, and `_cmd_triage`'s `aged_days`. The injectable `today=` test parameter is unchanged — only the default base moved from local to UTC. `reproduce.py` rewritten from a defect-demonstrator (explicit-param) into a regression test that freezes the engine clock at a pinned UTC instant and drives the DEFAULT path under `TZ=Pacific/Kiritimati`.
- **Verification**: `TZ=Pacific/Kiritimati uv run python reproduce.py` exits 0 (default base matches UTC verdict). Reverting any single guard to `date.today()` makes it exit 1 (default diverges from UTC). `python scripts/sync_plugin_assets.py --check` green; `uv run goc validate` clean (no FAILs).
- **Audit**: PASS — no principle touched, mechanical fix (timezone-base symmetry between write and read sides; closes the read-side hole the UTC-stamping audit missed).
- **Project impact**: n/a
- **Tests**: no pytest suite for this path; reproduce.py is the regression gate.
- **Bundled with**: none

## Closure verification (2026-05-27T02:33:45Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present

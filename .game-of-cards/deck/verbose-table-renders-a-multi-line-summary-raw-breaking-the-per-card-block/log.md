## 2026-09-14T05:44:52Z — Closure

- **What changed**: `goc/engine.py:3367-3382` — `render_table`'s
  `verbose >= 1` summary entry clips a multi-line `summary` to its first
  line and advertises the clip with an ellipsis plus a `goc show <title>`
  pointer, so the per-card detail block keeps its four-space indent. The
  clip shape is `_cmd_triage`'s existing summary-branch convention, not a
  third preview style; no character cap was added, so long single-line
  summaries still print in full.
- **Verification**: `reproduce.py` exits 1 before the change (2 continuation
  lines at column zero) and 0 after. All five assertions in the new
  `tests/test_verbose_table_multiline_summary.py` were re-run against a copy
  of the pre-fix `goc/engine.py` restored from HEAD: the indent, one-line,
  and clip-indicator assertions each fail there and pass after — the guard
  demonstrably catches the offender rather than only agreeing with the fix.
  On the real deck, the 43 of 757 cards carrying a multi-line summary now
  render one line each under `goc -v`. `uv run goc validate` exit 0;
  `scripts/sync_plugin_assets.py --check` and
  `scripts/port_skills_to_openclaw.py --check` clean after re-mirroring the
  engine into the three plugin payloads.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: 1147 passed / 0 failed / 0 xfailed (was 1142; +5 in
  `tests/test_verbose_table_multiline_summary.py`).
- **Bundled with**: n/a

## Closure verification (2026-09-14T05:45:13Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-09-14 — Closure' present

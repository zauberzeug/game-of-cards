## 2026-05-29T04:23:40Z — Closure

- **What changed**: goc/engine.py:1836 (`compute_values.value_for`), :1323 (`detect_advance_cycles`), :1349 (`_would_create_advance_cycle`) — guard non-list `advances`/`advanced_by` with `isinstance(..., list)` before iterating, matching the existing pattern at engine.py:1297.
- **Verification**: reproduce.py exits 0 with `value == own == 1.0`, `path == ["self"]`, no stderr warnings. Pre-fix: `value == 1.7`, `path == ['a', 'cycle']`, four phantom dangling-edge warnings.
- **Audit**: PASS — no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: 178 passed / 0 failed / 0 xfailed (full `uv run python -m unittest discover -s tests`). New regression module `tests/test_non_list_advances_guard.py` adds 4 cases covering `compute_values` (bare string + other non-list types) and both cycle walkers.
- **Bundled with**: n/a
- **Drive-by**: re-ran `scripts/port_skills_to_openclaw.py` to refresh `openclaw-plugin/skills/standup/SKILL.md`, which was drifted from `goc/templates/skills/standup/SKILL.md` since commit 07f76a7 (CI plugin-mirror-parity test was already red on main). Deterministic port; no manual edits.

## Closure verification (2026-05-29T04:24:04Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-29 — Closure' present

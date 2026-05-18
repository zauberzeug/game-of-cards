## 2026-05-18 — Closure

- **What changed**: `goc/engine.py:571`, `goc/engine.py:1591`, `goc/engine.py:2950` — added structured half-edge detection plus `goc repair-edges` preview/apply support, and taught `goc validate` to point half-edge failures at the repair command.
- **Verification**: Dirty temp-deck tests cover dry-run diff output, `--apply`, idempotence, cycle refusal, post-repair `goc validate`, and the validation remediation hint.
- **Audit**: PASS — no principle touched, mechanical fix.
- **Project impact**: n/a.
- **Tests**: `uv run pytest tests/test_repair_edges.py tests/test_new_wires_edges.py` — 8 passed; `python3 scripts/sync_plugin_assets.py --check` — OK; `uv run goc validate --quiet` — passed; `env GIT_CONFIG_GLOBAL=/dev/null uv run pytest` — 130 passed. Plain `uv run pytest` hit one environment-sensitive existing board test when global git user config was visible.
- **Bundled with**: n/a.

## Closure verification (2026-05-18T04:10:50Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 7/7 ticked
- [x] log-md-closure-entry — '## 2026-05-18 — Closure' present

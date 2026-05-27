## 2026-05-27T00:00:00Z — Closure

- **What changed**: `AGENTS.md` `## Common commands` — dropped the stale "No pytest suite exists yet" claim; now describes the `tests/` stdlib-`unittest` regression suite, adds the local run command to the code block, and names the `Run regression tests` CI step alongside build/console-script/`goc validate`.
- **Verification**: `tests/` holds 17 modules / 165 tests; `uv run python -m unittest discover -s tests` → 165 passed; `uv run goc validate` clean.
- **Audit**: PASS — no principle touched, mechanical doc fix.
- **Project impact**: n/a
- **Tests**: 165 passed / 0 failed / 0 xfailed

## Closure verification (2026-05-27T11:42:19Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present

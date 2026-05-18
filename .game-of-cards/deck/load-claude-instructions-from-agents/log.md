## 2026-05-18 — Closure

- **What changed**: `AGENTS.md` now carries the repo guidance that had lived in `CLAUDE.md`; `CLAUDE.md` is a one-line `@AGENTS.md` import. `goc/install.py` now writes or refreshes a Claude import pointer when Claude is installed and the briefing home is `AGENTS.md` or `CLAUDE.local.md`; `--briefing-target CLAUDE.md` remains the Claude-only inline path. Kickoff skill text now delegates import wiring to `goc install` / `goc upgrade`.
- **Verification**: `uv run goc validate` passed; `uv run python scripts/sync_plugin_assets.py --check` passed; `git diff --check` passed; `uv run python -m unittest tests.test_guidance_accuracy tests.test_version_surfaces` passed; nine targeted install/upgrade regression tests passed.
- **Audit**: PASS — no rubric configured; mechanical fix.
- **Project impact**: root guidance is cross-runtime by default, while Claude Code loads it through `@AGENTS.md`; future install/upgrade paths preserve the same shape unless the user explicitly chooses Claude-only `CLAUDE.md`.
- **Tests**: 9 targeted install/upgrade tests passed; 3 guidance/version tests passed; `tests.test_install` full suite ran 66 passed / 1 failed in `test_board_and_open_queue_surface_active_cards` due the pre-existing worker-display truncation issue unrelated to this change.
- **Bundled with**: n/a

## 2026-05-18 — Post-close amendment

- **What changed**: Clarified `--briefing-target` help text so the CLI describes the new CLAUDE.md import behavior for `AGENTS.md` and `CLAUDE.local.md`.
- **Verification**: `uv run python scripts/sync_plugin_assets.py --check`, `uv run goc validate --quiet`, `git diff --check`, and five focused install/help/import tests passed after the amendment.

## Closure verification (2026-05-18T03:44:15Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 8/8 ticked
- [x] log-md-closure-entry — '## 2026-05-18 — Closure' present

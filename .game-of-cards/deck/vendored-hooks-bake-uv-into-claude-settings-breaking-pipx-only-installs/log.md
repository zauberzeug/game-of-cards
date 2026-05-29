## 2026-05-29T13:46:13Z — Closure

- **What changed**: `goc/install.py:539-543` — `GOC_CLAUDE_HOOKS` registrations drop the `uv run ` prefix and emit `python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/<script>.py`, matching the plugin payload at `claude-plugin/hooks/hooks.json`. Test literals in `tests/test_install.py` (7 occurrences) updated to the new shape. This repo's `.claude/settings.json` regenerated. Plugin mirrors (`claude-plugin/`, `codex-plugin/`, `openclaw-plugin/`) auto-synced by `scripts/sync_plugin_assets.py`.
- **Verification**: `reproduce.py` exit 0 (post-fix); pre-fix command failed with `uv: not found` rc=127. Regression suite green (230 tests). `goc validate --quiet` clean (pre-existing untagged-DoD warnings only). `sync_plugin_assets.py --check` clean.
- **Audit**: PASS — no rubric configured; mechanical fix (remove unnecessary `uv` dependency from vendored hook registrations to align with the already-correct plugin path).
- **Project impact**: pipx-only consumers (one of two README-documented install paths) no longer get broken SessionStart / UserPromptSubmit / Stop hooks after `goc install --local-skills`.
- **Tests**: 230 passed / 0 failed / 0 xfailed.
- **Bundled with**: n/a.

## Closure verification (2026-05-29T13:46:27Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-29 — Closure' present

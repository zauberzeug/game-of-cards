## 2026-06-08T11:56:01Z — Closure

- **What changed**: Local Codex was moved from the stale `game-of-cards@zauberzeug-claude` plugin install to the direct `game-of-cards@game-of-cards` install, which created a 0.0.24 cache under `~/.codex/plugins/cache/game-of-cards/game-of-cards/0.0.24`; `goc/templates/skills/codex-kickoff/SKILL.md` now documents removing the stale marketplace install.
- **Verification**: `reproduce.py` reports old plugin enabled `False`, direct plugin enabled `True`, direct plugin version `0.0.24`, and no strict-YAML hazards in the active cache.
- **Audit**: PASS — no principle touched, mechanical plugin-cache migration and documentation fix.
- **Project impact**: Codex startup should stop warning about invalid GoC skill YAML after a restart because the enabled GoC plugin now resolves to the strict-YAML-safe direct 0.0.24 payload.
- **Tests**: `uv run python .game-of-cards/deck/codex-startup-loads-yaml-broken-plugin-cache/reproduce.py` passed; `uv run python -m unittest tests.test_skill_frontmatter_strict_yaml` passed; `python3 scripts/sync_plugin_assets.py --check` passed; `python3 scripts/port_skills_to_openclaw.py --check` passed; `uv run goc validate` exited 0 with pre-existing deck warnings.

## Closure verification (2026-06-08T11:56:29Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-06-08 — Closure' present

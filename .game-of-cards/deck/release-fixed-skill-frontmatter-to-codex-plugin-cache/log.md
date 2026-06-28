## 2026-06-08T04:15:00Z — Closure

- **What changed**: Release workflow run `27114008600` dispatched `v0.0.24` from `main`; the run completed successfully and pushed tag `v0.0.24` at release commit `260453dea355674e977eeeb8588575627e181c77`.
- **Verification**: `uv run python -m unittest tests.test_skill_frontmatter_strict_yaml` passed; raw `v0.0.24` payload inspection confirmed quoted frontmatter for `codex-plugin/skills/kickoff/SKILL.md`, `advance-card/SKILL.md`, `pull-card/SKILL.md`, and `next-card/SKILL.md`; PyPI and npm latest both reported `0.0.24`.
- **Audit**: PASS — no principle touched, release-propagation fix.
- **Project impact**: Codex plugin managers have a new version key beyond the stale `0.0.23` cache, carrying the strict-YAML-safe skill frontmatter.
- **Tests**: `uv run python -m unittest tests.test_skill_frontmatter_strict_yaml` passed; later full regression suite passed (`uv run python -m unittest discover -s tests`, 388 tests, 1 skipped).
- **Bundled with**: clawhub-package-publishes-pre-rewrite-package-json

## 2026-06-08T11:20:00Z — Later evidence

Codex still warned about invalid GoC skill YAML on startup on a host
where `game-of-cards@zauberzeug-claude` was enabled. The release itself
was present (`v0.0.24` exists upstream), but the separate
`zauberzeug-claude` marketplace snapshot pinned the GoC source to
`v0.0.23`, keeping the old YAML-broken cache active. Follow-up:
[codex-startup-loads-yaml-broken-plugin-cache](../codex-startup-loads-yaml-broken-plugin-cache/).

## Closure verification (2026-06-08T04:13:51Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — all 1 closed
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-06-08 — Closure' present

## 2026-05-04 — Closure

- **What changed**: Removed hard-coded project-local commit-helper references from GoC shipped skill templates and synced the dogfood `.claude/skills` copies.
- **Verification**: `rg -n "prepare-commit|Skill\\(prepare-commit\\)" goc/templates .claude goc/engine.py AGENTS.md CLAUDE.md README.md` returns no matches.
- **Sibling repo**: `../phasor-agents/.claude/skills/finish-card/SKILL.md` now loads `.game-of-cards/hooks/finish-card.md` for commit handoff; that hook owns the phasor-specific helper invocation.
- **Tests**: `.venv/bin/goc validate` passed.

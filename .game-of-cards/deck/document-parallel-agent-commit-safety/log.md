## 2026-05-18 — Closure

- **What changed**: Added a `Parallel-Agent Commit Safety` section to `AGENTS.md`; added the same shared-index commit handoff to `goc/templates/skills/finish-card/SKILL.md`; updated `.claude/skills/finish-card/SKILL.md`, `claude-plugin/skills/finish-card/SKILL.md`, and `openclaw-plugin/skills/finish-card/SKILL.md`.
- **Verification**: `uv run python scripts/sync_plugin_assets.py --check`, `uv run goc validate --quiet`, and `git diff --check` passed.
- **Audit**: PASS — no rubric configured; mechanical documentation/workflow guidance change.
- **Project impact**: Agents now have an explicit safe commit sequence for shared local `main`: wait for a free index, stage explicit paths, verify the staged set, commit with pathspecs, avoid stash/destructive cleanup, and use a worktree for risky shared-main commit prep.
- **Tests**: 3 checks passed / 0 failed.
- **Bundled with**: n/a

## Closure verification (2026-05-18T03:54:41Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-18 — Closure' present

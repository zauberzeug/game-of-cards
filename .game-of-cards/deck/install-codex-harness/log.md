## 2026-05-04

- Implemented `--agents` selection for `goc install`/`goc upgrade` with supported harnesses `claude` and `codex`; no-flag default remains `claude`.
- Split planned writes into `shared`, `codex`, and `claude` ownership. `--agents codex` writes deck/config/pre-commit scaffold plus `AGENTS.md` only; Claude skills, hook, and `CLAUDE.md` are only planned/written when `claude` is selected.
- Updated `AGENTS_GOC.md` and this repo's installed `AGENTS.md` block to be Codex-safe: no `Skill(...)` notation and no `.claude/skills/` dependency.
- Documented `goc install --agents codex` and repo-local `uv run goc install --agents codex` in `README.md`.
- Verification:
  - `uv run goc install --dry-run --agents codex`
  - `uv run --project /Users/rodja/Projects/game-of-cards goc install --agents codex` in `/private/tmp/goc-codex-smoke.inlLm0`
  - confirmed no `.claude/` and no `CLAUDE.md` in the Codex-only smoke repo
  - confirmed `AGENTS.md` had no `Skill(...)` or `.claude/skills` references
  - `uv run --project /Users/rodja/Projects/game-of-cards goc new codex-harness-smoke --gate none --tag infra`
  - `uv run --project /Users/rodja/Projects/game-of-cards goc validate`
  - `uv run goc validate` in this repo
  - `uv run python -m compileall goc`
  - default Claude smoke install in `/private/tmp/goc-claude-smoke.W923ae`

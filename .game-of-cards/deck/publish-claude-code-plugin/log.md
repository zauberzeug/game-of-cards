## 2026-05-06: implementation round 1

Landed:
- `.claude-plugin/marketplace.json` at repo root — single-plugin marketplace with source `./claude-plugin`, enabling `/plugin marketplace add zauberzeug/game-of-cards && /plugin install game-of-cards@game-of-cards`
- `.github/workflows/ci.yml` step "Verify plugin version lockstep" — guards pyproject.toml ↔ claude-plugin/plugin.json ↔ marketplace.json metadata version drift
- `.github/workflows/pages.yml` llms.txt — added "Lean alternative for Claude Code (no checked-in skills)" section pointing LLMs at the marketplace install commands
- `README.md` Try-it block — synced with website's LLM-direction paragraph (`If you are an LLM and the user asked you to set this up: fetch /llms.txt …`)
- zauberzeug-claude PR #8 — adds game-of-cards as a `git-subdir` source pointing to the public repo's `claude-plugin/` subdirectory; uses default-branch ref per the lockstep policy

Open verification (DoD-6):
- Live smoke-test of `/plugin install game-of-cards@game-of-cards` (own-repo path) and `/plugin install game-of-cards@zauberzeug-claude` (post-merge) on a clean repo
- Specific risk to verify: symlinks under `claude-plugin/skills` and `claude-plugin/hooks/*.py` point OUTSIDE the plugin directory (into `goc/templates/`). Claude Code's docs warn that plugins copied to the cache can't reference files outside their dir. Confirm whether the symlinks resolve at clone-time (file copy) or remain as symlinks pointing at non-existent locations after Claude Code's plugin install.

## 2026-05-06: decision recorded

Q1 marketplace: list in private zauberzeug-claude marketplace (PR there) + LLM-only direct-install path documented in goc docs; pursue Anthropic-official marketplace later. Q2 versioning: marketplace entries point at default branch, plugin.json carries version stamp, add CI tripwire enforcing pyproject.toml::version == claude-plugin/.claude-plugin/plugin.json::version. Q3 goc-on-PATH: runtime-only check via the existing bootstrap-error-when-cli-not-on-path card; LLM install instructions document uv tool install game-of-cards as prerequisite. — B+C unblocks Claude Code lean-install today without waiting on Anthropic review. zauberzeug-claude is private team-internal so it stays unmentioned in goc public docs. Direct-install path is LLM-targeted because human users get told 'pipx install game-of-cards + goc install' (the canonical recipe via llms.txt); the plugin path is the LLM-recognized lean alternative when running inside Claude Code. CI tripwire makes the lockstep policy enforced rather than aspirational — version drift was caught manually this session, won't be next time.. Gate session → none.

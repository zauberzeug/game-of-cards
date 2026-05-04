---
title: goc-multi-agent-shim-which-agents-at-v1
summary: "Spec-Kit's `--integration <agent>` flag is the niche-standard pattern for multi-agent shim install — the same `init` populates per-agent shim directories selectively. GoC needs the same `goc install --agents claude,cursor,codex` flag and shim templates per supported agent. The decision this card carries is which agents to ship at v1: Claude-only (smallest, ship the loop, expand) vs claude+cursor+codex day-one (broader reach, more shim templates and per-agent compatibility quirks to maintain). OpenCode is FREE because it natively reads `.claude/skills/`. Hooks do NOT port (only Claude Code has PreToolUse/PostToolUse), so the silent-runtime mode stays Claude-specific regardless of v1 scope."
status: open
stage: null
contribution: medium
created: 2026-05-03
closed_at: null
human_gate: none
advances: [goc-ship-game-of-cards-as-cross-agent-cli]
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] Decision recorded: v1 agent set (Claude-only, claude+cursor, claude+cursor+codex, etc.) with rationale
  - [ ] `goc install --agents <list>` flag implemented; `goc install` with no flag defaults to `claude` (or whatever the v1 default decision says)
  - [ ] For each v1 agent, a `templates/agents/<agent>/` directory exists with the shim files for that agent's convention (e.g., `.cursor/rules/goc.mdc`, `.codex/...`, `.github/copilot-instructions.md`)
  - [ ] Per-agent shim content is generated, not duplicated — the slash-command surface and skill descriptions come from a shared source; only the *file format and path convention* differs per agent
  - [ ] Documentation: README on the new repo lists supported agents at v1, with a clear "to add agent X, file an issue / PR template Y" section for community extension
  - [ ] OpenCode mentioned explicitly as free (reads `.claude/skills/` natively); hooks-not-supported caveat documented
---

# Multi-agent shim — which agents at v1?

## Decision

*Resolved 2026-05-03:* Claude + extension hook

*Reasoning:* shipping fast on Claude+AGENTS.md covers six agents indirectly, and community PRs grow per-agent shims post-v1 the way Spec-Kit's integrations grew
## Recommendation (for the human deciding)

**Option C** unless there's a specific Cursor/Codex user lined up to need v1. The scope-vs-reach tradeoff strongly favors shipping fast on Claude + AGENTS.md (which already covers the six-agent set indirectly), with a documented extension path. Spec-Kit's growth from 3 → 30+ agents happened post-v1 via PRs, not in the launch sprint.

The argument for Option B is real if Zauberzeug has a concrete cross-agent use case (e.g., "we want to use GoC on the labkit project where the team uses Cursor"). Otherwise it's premature.

## What

After the decision lands:

1. **Implement `goc install --agents`** — Click multi-value flag, default from a config constant, validates against the registered agent shim directories.
2. **Per-agent shim templates** in `templates/agents/<agent>/`. For each agent at v1, author the shim files matching that agent's convention.
3. **Shared shim content** — slash-command descriptions, skill summaries — comes from a single source-of-truth YAML or JSON in `templates/`, then per-agent renderers convert to that agent's format.
4. **README on the new repo** lists supported agents with a contribution guide for adding new ones.

## Cross-references

- Parent epic: `goc-ship-game-of-cards-as-cross-agent-cli`
- Sibling install card: `goc-install-command-scaffolds-repo` (consumes per-agent shim templates)
- Sibling AGENTS.md card: `goc-write-agentsmd-alongside-claudemd` (covers the agent-agnostic guidance regardless of which agents have shims)
- Prior art: Spec-Kit `--integration <agent>` (`docs/reference/integrations.md` in github/spec-kit)
- OpenCode skill compat: sst/opencode reads `.claude/skills/` natively → free, no shim needed

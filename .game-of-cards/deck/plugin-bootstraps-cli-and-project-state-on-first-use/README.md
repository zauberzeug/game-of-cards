---
title: plugin-bootstraps-cli-and-project-state-on-first-use
summary: "When a user installs the GoC Claude Code plugin via the marketplace and then asks the agent to use GoC in a repo, the plugin should bootstrap everything else: ensure the `goc` CLI is on PATH (offer to install via `uv tool install game-of-cards`), create `.game-of-cards/deck/` if missing, merge the AGENTS.md / CLAUDE.md GoC blocks. The user should not need to know about `goc install` as a separate step — installing the plugin and saying 'use GoC here' should be sufficient."
status: done
stage: null
contribution: high
created: 2026-05-07
closed_at: 2026-05-07
human_gate: none
advances:
  - support-external-game-of-cards-state-location
advanced_by:
  - publish-claude-code-plugin
  - claude-install-defaults-to-plugin-path
tags: [story, infra]
definition_of_done: |
  - [x] A plugin-provided bootstrap skill (working title: `Skill(bootstrap)` — alt names: `Skill(install)`, `Skill(setup)`; pick during implementation; must not collide with existing skills) detects whether the current repo is GoC-initialized (presence of `.game-of-cards/deck/`) and offers to bootstrap if not
  - [x] The bootstrap skill ensures `goc` is on PATH; if missing, asks the user for confirmation and runs `uv tool install game-of-cards` (fallback to `pipx install game-of-cards` if `uv` is missing — fallback chain documented in skill body)
  - [x] The bootstrap skill runs `goc install` (in its lean mode per `claude-install-defaults-to-plugin-path`) to create `.game-of-cards/` project state and merge AGENTS.md / CLAUDE.md GoC blocks
  - [x] Subsequent skill invocations (after bootstrap) skip the bootstrap path silently — `Skill(create-card)`, `Skill(scan-deck)`, etc. work without re-running bootstrap
  - [x] CLAUDE_GOC.md / AGENTS_GOC.md guidance carries an explicit instruction so any agent reading the GoC block knows to call the bootstrap skill on first use of a fresh repo, not assume it has already happened
  - [x] User journey verified end-to-end on a fresh repo: (1) `/plugin marketplace add zauberzeug/game-of-cards`; (2) `/plugin install game-of-cards@game-of-cards`; (3) user asks Claude "use GoC here"; (4) plugin auto-bootstraps with at most two confirmations (CLI install if missing, project-state scaffolding); (5) user can immediately ask "create a card for X" and it works
  - [x] Skill body documents what is checked, what is created, and what user confirmations to expect — so the user can predict the bootstrap behavior before invoking it
  - [x] `uv run goc validate` passes
---

# Plugin bootstraps CLI and project state on first use

## Why

Two entry points exist for adopting GoC in Claude Code:

1. **CLI-first** (canonical, covered by `claude-install-defaults-to-plugin-path`): user prompts agent → agent installs `goc` CLI → agent runs `goc install` → `goc install` reminds about (or directly invokes via `claude -c`) the plugin install.
2. **Plugin-first** (this card): user installs the plugin themselves via Claude Code's `/plugin install`, then later asks the agent to use GoC in a repo. The plugin must do the rest — there's no agent-driven `goc install` step in the user's mental model.

The plugin-first journey is the natural one for users who:
- Discovered GoC via Claude Code's plugin marketplace UI (browse → install → "what can this do?")
- Already have GoC plugin installed from a prior project, opening a new repo for the first time
- Were told by a teammate "install the GoC plugin and try it"

In all three cases the user has already taken the install step and now expects "it just works." If they have to learn about `goc install` as a separate command, the plugin-first journey feels broken.

## What

The plugin ships a bootstrap skill that runs idempotently. On any fresh repo, the agent (per CLAUDE_GOC.md guidance carried by the plugin) invokes the bootstrap skill before doing anything else. The skill:

1. Checks if `.game-of-cards/deck/` exists — if yes, exits silently (already bootstrapped).
2. Checks if `goc` is on PATH — if no, asks user to install via `uv tool install game-of-cards` (fallback `pipx install game-of-cards` if `uv` missing).
3. Runs `goc install` (in the lean mode defined by `claude-install-defaults-to-plugin-path`) — creates `.game-of-cards/`, merges AGENTS.md/CLAUDE.md.
4. Confirms to the user that GoC is ready and suggests the next step (e.g., "what should the first card be?").

User-visible journey from the user's POV:

1. User: *"use GoC in this repo"* (or similar)
2. Plugin's bootstrap skill kicks in (per CLAUDE_GOC.md guidance)
3. Agent: *"Install goc CLI? (uv tool install game-of-cards)"* → user confirms (skip if already installed)
4. Agent: *"Set up GoC in this repo? (creates .game-of-cards/, updates CLAUDE.md)"* → user confirms
5. Done. User asks "create a card for X" and it works.

At most two confirmations on first use; zero on subsequent repos with goc CLI already installed.

## Relationship to other cards

- **Depends on `claude-install-defaults-to-plugin-path`**: that card defines `goc install`'s lean mode. This card calls into it. If `claude-install-defaults-to-plugin-path` is not yet implemented, `goc install` would still vendor `.claude/skills/`, defeating the plugin-first cleanliness.
- **Depends on `publish-claude-code-plugin`**: the plugin must be published / installable for users to get to this entry point.
- **Sibling to `claude-install-defaults-to-plugin-path`**: covers a different entry point (plugin-first vs CLI-first). Together they cover both bootstrap paths.

## Notes

- The bootstrap skill name should be picked during implementation. Candidates: `Skill(bootstrap)`, `Skill(install)`, `Skill(setup)`. Avoid colliding with the existing 11 skills (advance-card, card-schema, create-card, decide-card, deck, extend-deck, finish-card, improve-deck, next-card, pull-card, scan-deck).
- Bootstrap idempotency is critical: every skill invocation should NOT re-run bootstrap. The check is "does `.game-of-cards/deck/` exist?" — cheap, single-shot.
- An open question: should existing skills (e.g., `Skill(create-card)`) themselves call bootstrap if they detect uninitialized state? That's auto-bootstrap on first card creation, no separate skill invocation needed. Simpler UX but couples every skill to the bootstrap check. Defer this decision to implementation.
- This card and `claude-install-defaults-to-plugin-path` share a common investigation: what does `/plugin install` actually DO under the hood? If it just writes a state file in `~/.claude/`, the CLI can do that directly (removing the slash-command step from both bootstrap journeys). The investigation lives on `claude-install-defaults-to-plugin-path`'s DoD; this card inherits whatever answer it produces.

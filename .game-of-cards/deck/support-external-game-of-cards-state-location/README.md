---
title: support-external-game-of-cards-state-location
summary: "Track the repo-footprint redesign: GoC project state should live under `.game-of-cards` and generated runtime affordances should not have to be checked into consuming repositories. The direction is `.game-of-cards/deck` plus the existing `.game-of-cards/config.yaml`, optional skill/hook installation, and agent plugins for Claude Code, Codex, and later OpenClaw."
status: active
stage: null
contribution: high
created: 2026-05-04
closed_at: null
human_gate: session
advances: [ship-game-of-cards-as-cross-agent-cli]
advanced_by: [move-deck-into-game-of-cards-directory, make-skill-and-hook-installation-optional, provide-claude-code-plugin-for-skills-and-hooks, provide-codex-plugin-for-skills-and-hooks, provide-openclaw-plugin-for-skills-and-hooks, publish-claude-code-plugin, publish-codex-plugin, publish-openclaw-plugin, claude-install-defaults-to-plugin-path, plugin-bootstraps-cli-and-project-state-on-first-use, bundle-goc-engine-inside-plugin-payload, make-claude-md-and-agents-md-merge-opt-in-via-skill]
tags: [epic, story, infra, api-contract]
definition_of_done: |
  - [x] Deck storage moves under `.game-of-cards/deck` with compatibility or migration for existing root `deck/` repos
  - [x] Runtime-neutral config remains under `.game-of-cards` (currently `.game-of-cards/config.yaml`) and all docs use one spelling
  - [x] Skill/hook installation is optional and users can install CLI-only GoC without generated agent files
  - [x] Claude Code skills/hooks are available through a plugin path rather than only checked-in repo files
  - [ ] Codex skills/hooks are available through a comparable plugin path
  - [x] OpenClaw plugin direction supersedes the blocked OpenClaw harness card
  - [x] Plugin publication is tracked as explicit release work
  - [x] README/AGENTS guidance explains what is project state, what is runtime installation, and what should be checked in
  - [x] `uv run goc validate` passes
---

# Support not-checked-in Game of Cards state and runtime files

## Why

The current install story is repo-first: `goc install` scaffolds repo-visible skills, hooks, guidance, and a root `deck/`. That works for dogfooding, but it makes GoC feel like vendored project code and puts generated runtime files in the consuming repository.

The clarified direction is "not checked in", not necessarily "stored outside the repo checkout". The best default is to put GoC-owned project state under `.game-of-cards`: the deck at `.game-of-cards/deck` and config under the same directory. Runtime affordances such as skills and hooks should become optional installation/plugin concerns, not mandatory checked-in files.

## Split

This is now an epic-style parent. The implementation is split across:

- `move-deck-into-game-of-cards-directory`
- `make-skill-and-hook-installation-optional`
- `provide-claude-code-plugin-for-skills-and-hooks`
- `provide-codex-plugin-for-skills-and-hooks`
- `provide-openclaw-plugin-for-skills-and-hooks`
- `publish-game-of-cards-agent-plugins`

## Remaining session topics

The direction is clearer, but there are still architectural decisions:

- Whether `.game-of-cards` itself is checked in by default, ignored by default, or user-selectable.
- Whether the existing `.game-of-cards/config.yaml` spelling stays canonical or a `config.yml` alias is supported.
- How GitHub Actions `pull-card` works when the deck is not committed with the code it edits.
- What minimal repo-visible marker remains so agents can discover GoC when skills/hooks are plugin-installed.

## Shape

Keep `goc` as the stable engine and separate three concerns:

- Project state: `.game-of-cards/deck` and `.game-of-cards/config.yaml`.
- Repo guidance: a small marker or generated AGENTS.md block that can be checked in when desired.
- Runtime affordances: agent plugins or optional local installs for skills and hooks.

The key invariant: queue safety, validation, and DoD closure must not depend on whether skills/hooks are checked into the project repo.

## Decision

*Resolved 2026-05-05:* (1) .game-of-cards/ is checked in by default but users may gitignore it; (2) config.yaml stays canonical, no .yml alias; (3) pull-card runs in local sessions or via cron — no CI commitment required when the deck is uncommitted; (4) the AGENTS.md/CLAUDE.md <!-- BEGIN GOC --> marker block is the canonical repo-visible discovery surface, no extra dotfile

*Reasoning:* Anchors every child card to one consistent stance: the deck is project planning history (so checked-in is the team default), one config spelling avoids surface-area drift, and dropping the CI-must-work constraint unblocks the gitignore-friendly path without inventing branch/issue-sync machinery. Reusing the existing marker block avoids a second discovery mechanism.

## Session required

8 of 9 DoD items are now checked. The remaining item — Codex skills/hooks via a comparable plugin path — is tracked by `provide-codex-plugin-for-skills-and-hooks`, which is parked at `human_gate: session`. Lower the gate on that card to unblock this epic's final closure.

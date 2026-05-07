---
title: publish-claude-code-plugin
summary: Publish the Game of Cards Claude Code plugin so users can install it without checking generated `.claude/skills` and hook files into source control. Distribution-only work; the plugin payload already exists at `claude-plugin/`.
status: active
stage: null
contribution: medium
created: 2026-05-06
closed_at: null
human_gate: none
advances: [support-external-game-of-cards-state-location, claude-install-defaults-to-plugin-path]
advanced_by: [provide-claude-code-plugin-for-skills-and-hooks]
tags: [story, infra]
definition_of_done: |
  - [x] Publication target chosen (B+C: zauberzeug-claude private marketplace via PR + LLM-only direct-install via repo-root `.claude-plugin/marketplace.json`; A=anthropics/claude-code-plugins deferred) and recorded in Decision section
  - [x] Versioning policy documented (lockstep with goc PyPI version; marketplace entries point at default branch, plugin.json carries the version stamp; CI tripwire added in `.github/workflows/ci.yml` step "Verify plugin version lockstep" enforcing pyproject.toml::version == claude-plugin/.claude-plugin/plugin.json::version == .claude-plugin/marketplace.json::metadata.version)
  - [x] Release workflow exists — existing `.github/workflows/release.yml` triggers on `v*` tag push and ships the wheel to PyPI; plugin payload at `claude-plugin/` travels with the same tag; marketplace.json refs default branch so consumers track main
  - [x] Published artifact installable by a fresh consumer environment with `goc` on PATH — own-repo path live as of this commit (`/plugin marketplace add zauberzeug/game-of-cards && /plugin install game-of-cards@game-of-cards`); zauberzeug-claude path live once PR https://github.com/zauberzeug/zauberzeug-claude/pull/8 merges
  - [x] README + llms.txt document the install path and compatibility — LLM-direction block synced from website to README; `/llms.txt` gains a "Lean alternative for Claude Code" section with the marketplace install commands; canonical pipx-install recipe unchanged
  - [ ] Smoke-test or release-verification step confirms skills + hooks resolve through the plugin path on a clean repo (post-merge user verification)
  - [x] `uv run goc validate` passes
---

# Publish the Claude Code plugin

## Why

The plugin payload already exists at `claude-plugin/` (skills + hooks symlinked into `goc/templates/` so the wheel and the plugin ship the same bytes). The big epic `provide-claude-code-plugin-for-skills-and-hooks` is closed. What's missing is **distribution**: today a user wanting the leaner installation path has to clone this repo and `claude plugin install /path`. That's not a release.

This card's job is to turn `claude-plugin/` into an artifact that consumers install without touching this repo's source tree.

## Session required

Three coupled choices need a working session:

1. **Marketplace target.** Options:
   - **A. Anthropic's official `anthropics/claude-code-plugins` marketplace** — most discoverable, requires PR + review against their listing rules.
   - **B. Own marketplace repo** under `zauberzeug/` — fully self-served, less discoverable, requires users to add it via `claude marketplace add`.
   - **C. Direct git install only** — `claude plugin install https://github.com/zauberzeug/game-of-cards` — zero infra, no review gate, but no upgrade UX.
   - These aren't mutually exclusive; the question is which we treat as the canonical install path in docs.

2. **Versioning + release coupling.** The parent epic decided "plugin version locked to goc package version, released together by tag." That implies the publish step happens inside the existing `vX.Y.Z` tag workflow rather than as a separate release. Confirm + wire it up (which subset of the existing GH Actions triggers on the marketplace push?).

3. **Prerequisite on `goc` CLI.** Plugin skills shell out to `goc`; without `goc` on PATH the plugin is broken. The card `bootstrap-error-when-cli-not-on-path` already exists to make this fail loudly. Decide: do we want the plugin install to *check* for `goc` (warning at install time) or only at first invocation?

## Scope

This card is Claude-only. Codex, OpenClaw, and any future Cursor publishing live in their own cards (`publish-codex-plugin`, `publish-openclaw-plugin`, future `publish-cursor-plugin`). Splitting was explicit: there's no good reason to gate the first plugin's release on the others.

## Notes

- Supersedes the Claude portion of the previous bundled card `publish-game-of-cards-agent-plugins`.
- The `claude-plugin/.claude-plugin/plugin.json` is at version 0.0.4; that needs to track `pyproject.toml`'s version per the lockstep decision.

## Decision

*Resolved 2026-05-06:* Q1 marketplace: list in private zauberzeug-claude marketplace (PR there) + LLM-only direct-install path documented in goc docs; pursue Anthropic-official marketplace later. Q2 versioning: marketplace entries point at default branch, plugin.json carries version stamp, add CI tripwire enforcing pyproject.toml::version == claude-plugin/.claude-plugin/plugin.json::version. Q3 goc-on-PATH: runtime-only check via the existing bootstrap-error-when-cli-not-on-path card; LLM install instructions document uv tool install game-of-cards as prerequisite.

*Reasoning:* B+C unblocks Claude Code lean-install today without waiting on Anthropic review. zauberzeug-claude is private team-internal so it stays unmentioned in goc public docs. Direct-install path is LLM-targeted because human users get told 'pipx install game-of-cards + goc install' (the canonical recipe via llms.txt); the plugin path is the LLM-recognized lean alternative when running inside Claude Code. CI tripwire makes the lockstep policy enforced rather than aspirational — version drift was caught manually this session, won't be next time.

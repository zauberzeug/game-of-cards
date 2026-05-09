---
title: provide-openclaw-plugin-for-skills-and-hooks
summary: "Replace the blocked OpenClaw harness direction with a later OpenClaw plugin/runtime package for Game of Cards skills and hooks. This supersedes `install-openclaw-harness` and should wait until the Claude/Codex plugin pattern is clear or an OpenClaw consumer appears."
status: open
stage: null
contribution: high
created: 2026-05-05
closed_at: null
human_gate: session
advances:
  - support-external-game-of-cards-state-location
  - publish-openclaw-plugin
advanced_by:
  - bundle-goc-engine-inside-plugin-payload
tags: [story, infra]
definition_of_done: |
  - [x] `install-openclaw-harness` is marked superseded with a log entry pointing here
  - [ ] OpenClaw plugin/runtime extension format is confirmed from current upstream docs or source before implementation
  - [ ] Plugin supplies GoC instructions/skills/hooks through OpenClaw's native mechanism where possible
  - [ ] Plugin delegates durable state to `.game-of-cards` and the `goc` CLI
  - [ ] Plugin emits skills as `SKILL.md` directories (per OpenClaw's documented skill format) and chosen skill-precedence tier (workspace / project agent / personal agent / managed / bundled) is recorded in this card's log
  - [ ] Plugin lists on the ClawHub registry (<https://clawhub.ai>), or rationale for skipping ClawHub is recorded in this card's log
  - [ ] Docs list OpenClaw plugin support separately from repo-local harness installation
  - [ ] Smoke test confirms OpenClaw can discover/use the plugin in a fresh repo
  - [ ] `uv run goc validate` passes
---

# Provide an OpenClaw plugin for skills and hooks

## What is OpenClaw

OpenClaw is an open-source personal AI assistant that runs on the user's own devices and answers across messaging channels. **It is a distinct product from OpenCode (sst/opencode)** — do not assume the deck's "OpenClaw" is a typo for "OpenCode"; they are unrelated runtimes with separate cards.

Identity anchors (verified 2026-05-09 against upstream sources):

- Repository: <https://github.com/openclaw/openclaw> — tagline *"Your own personal AI assistant. Any OS. Any Platform. The lobster way. 🦞"*
- Site: <https://openclaw.ai>; docs: <https://docs.openclaw.ai>
- Runtime: Node 24 recommended, Node 22.16+ minimum
- Install: `npm install -g openclaw@latest` (pnpm/bun supported)
- Setup verb: `openclaw onboard`
- Skills format: each skill is a directory containing `SKILL.md` with YAML frontmatter (`name`, `description` required); see <https://docs.openclaw.ai/tools/skills>
- Skill precedence (highest first): workspace → project agent → personal agent → managed/local → bundled → extra skill folders
- Public skills registry: ClawHub at <https://clawhub.ai>; consumer-side install verb is `openclaw skills install`

OpenCode, by contrast, reads `.claude/skills/` natively (see `ABOUT.md`) and gets GoC for free via the Claude harness path; that is why there is no separate OpenCode plugin card.

## Why

The previous OpenClaw work was framed as another `goc install --agents openclaw` repo-local harness. The clarified direction is plugin-first: Claude Code and Codex plugins first, then OpenClaw later. This card replaces the blocked harness card.

## Timing

This was intentionally later-stage work. The "wait until the plugin shape is proven for a primary runtime" guard is now satisfied: `publish-claude-code-plugin` and `bundle-goc-engine-inside-plugin-payload` both closed by 2026-05-08, so the Claude plugin pattern (vendored engine + bin wrapper + marketplace listing) is concrete reference material. The card remains `human_gate: session` because the OpenClaw skills/extension format and publication path still need a discovery sitting before implementation.

## Implementation anchors (for the eventual session)

- **Bundling**: confirm whether OpenClaw skills can shell out to a host-installed `goc` CLI (Python), or whether the plugin must vendor a Python runtime alongside the Node-based OpenClaw host. The Claude plugin's vendored-engine pattern (`claude-plugin/goc/` + `bin/goc` wrapper) is the reference shape — see `bundle-goc-engine-inside-plugin-payload`. OpenClaw running on Node makes the analogue non-trivial.
- **Hook surface**: confirm what session/lifecycle events OpenClaw exposes to skills (the docs reference `/new`, `/reset`, `/compact` chat commands plus a session model) and whether any can carry GoC's SessionStart / UserPromptSubmit / Stop semantics. If not, document the gap explicitly rather than ship a half-working analogue.
- **Skill tier choice**: pick which precedence tier the GoC plugin lands in. Likely `bundled` for a published-on-ClawHub plugin, but `managed` may be more appropriate for the per-workspace state model GoC needs.
- **Distribution**: confirm whether ClawHub is the only channel, or whether the plugin should also publish as a plain npm package (parallel to the Claude marketplace listing).

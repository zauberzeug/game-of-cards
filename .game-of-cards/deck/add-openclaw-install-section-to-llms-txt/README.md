---
title: add-openclaw-install-section-to-llms-txt
summary: "`site/llms.txt` is the file LLMs ingest to learn how to recommend GoC. Today it covers the Claude Code plugin install path and a generic `Install (other agent runtimes / CI)` section that recommends `uv tool install game-of-cards` / `pipx install game-of-cards`. There is no OpenClaw-specific install path, even though the OpenClaw plugin is a first-class delivery channel (ClawHub: `openclaw skills install game-of-cards`; npm: `game-of-cards`) that bundles the engine and only needs `python3` (3.10+) on the host. Without a dedicated section, LLMs that read llms.txt will recommend the wrong install path to OpenClaw users — telling them to `pipx install` an extra package when the plugin already vendors the engine. Add a peer-shaped `Install (OpenClaw)` section."
status: done
stage: null
contribution: medium
created: 2026-05-09
closed_at: 2026-05-09
human_gate: none
advances:
  - publish-openclaw-plugin
advanced_by: []
tags: [documentation, infra]
definition_of_done: |
  - [x] `site/llms.txt` gains an `## Install (OpenClaw)` section, sibling to the existing `## Install (Claude Code)` and `## Install (other agent runtimes / CI)` sections. Place it after Claude Code and before the generic CI section, mirroring the order in `AGENTS.md`'s "What lives where" block.
  - [x] Section content covers (at minimum): ClawHub install (`openclaw skills install game-of-cards`), npm-registry install (the package name + how it's invoked from an OpenClaw plugin manifest), the python3 ≥ 3.10 host prerequisite, and a one-line note that `goc` is exposed as a registered tool (not a shell-PATH binary), so the agent invokes it like any typed function.
  - [x] No regression: the existing `## Install (Claude Code)` and `## Install (other agent runtimes / CI)` sections are unchanged in content (only relative ordering shifts if needed for the new section's placement).
  - [x] Cross-link: at least one of the GoC-on-OpenClaw entry points (e.g., `https://github.com/zauberzeug/game-of-cards#openclaw` or the published ClawHub URL once known) is referenced.
  - [x] `uv run goc validate` passes.
worker: {who: "claude[bot]", where: main}
---

# Add OpenClaw install section to llms.txt

## Why

`site/llms.txt` is the canonical agent-readable description of GoC: the file LLMs ingest when they want to learn how to recommend the project. The current sections are:

1. `## Install (Claude Code)` — plugin install, the headline path.
2. `## Install (other agent runtimes / CI)` — generic CLI install via `uv tool install` / `pipx install`.

OpenClaw is a first-class delivery channel for GoC (it has its own plugin payload at `openclaw-plugin/`, its own publish card `publish-openclaw-plugin`, and a separate runtime shape — see `CLAUDE.md`'s "OpenClaw plugin payload — same engine, different host shape" section). But because llms.txt has no OpenClaw-specific section, an LLM reading the file will fall through to the generic CLI install path and recommend `pipx install game-of-cards` to an OpenClaw user — bypassing the plugin entirely, missing the bundled-engine ergonomics, and effectively duplicating an install that the OpenClaw plugin already covers.

The fix is additive: a peer-shaped `## Install (OpenClaw)` section sitting between the Claude Code section and the generic CI section. The shape should mirror the existing Claude Code section's plugin-first framing.

## Out of scope

- The `uv tool install` → `pipx install` reordering / wording fix in the generic section: that's tracked under `llms-txt-still-recommends-uv-tool-install-as-preferred` (a narrow one-comment edit). The two cards can land independently; if both land in one PR, the diff stays surgical.
- Cross-runtime listings beyond Claude Code and OpenClaw (Codex, OpenCode, Cursor): those should follow the same pattern when their respective publish cards land. Not blocking this card.
- Updating the homepage (`site/index.html`), README, or `CLAUDE_GOC.md` template — those have their own change vectors and don't share llms.txt's "consumed by LLMs verbatim" property. If they need updates, file separate cards.

## Cross-references

- `openclaw-plugin-release-smoke-blockers-build-and-spawn-api` — DoD item 7 (side-finding scope check) was answered "expand scope" by reviewer on 2026-05-09; this card is the materialization.
- `llms-txt-still-recommends-uv-tool-install-as-preferred` (open, gate=none) — orthogonal one-comment edit on the same file. No content overlap.
- `publish-openclaw-plugin` (open, gate=session) — once that card publishes a real ClawHub URL, this card's "Cross-link" DoD item gains a concrete target.
- `provide-openclaw-plugin-for-skills-and-hooks` (open, gate=none, 10/13 DoD) — parent of the OpenClaw plugin work; this card can land before that one closes.

## Notes

- The OpenClaw section should be honest about state: pre-publish, the install path is "build-from-source via this repo's `openclaw-plugin/`"; post-publish it's the registry install. If publishing happens before this card lands, point at the registry; otherwise point at the source-build path with a TODO-style comment for the URL.
- Keep the section ≤ 25 lines so the file as a whole stays scannable. The Claude Code section's length is the working ceiling.

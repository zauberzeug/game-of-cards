---
title: write-agentsmd-alongside-claudemd
summary: "AGENTS.md is the Linux-Foundation-stewarded shared-substrate convention now read by Claude Code, Codex, Cursor, Copilot, OpenCode, and Aider. Spec-Kit, BMAD, Agent OS, and Ruler all write AGENTS.md by default; only Claude-specific extras go into CLAUDE.md. `goc install` should write/merge an `AGENTS.md` block alongside the CLAUDE.md sections so the methodology is visible to all six major agent runtimes, not just Claude. Same marker-bounded merge pattern as CLAUDE.md (so `goc upgrade` can re-sync without clobbering user content). Content is the agent-agnostic GoC briefing — deck-first mode, slash-command surface (skills auto-port to OpenCode; Cursor/Codex use explicit invocations), what `pull-card` / `pipx` mean."
status: open
stage: null
contribution: medium
created: 2026-05-03
closed_at: null
human_gate: session
advances:
  - ship-game-of-cards-as-cross-agent-cli
advanced_by: []
tags: [story, infra, documentation]
definition_of_done: |
  - [x] `goc install` writes `AGENTS.md` (creates if absent, appends marker-bounded section if present) at the repo root
  - [x] AGENTS.md content is agent-agnostic: no `Skill(...)` notation (Claude-specific); uses `goc <verb>` and "ask the agent to ..." phrasings instead
  - [x] Marker pattern matches CLAUDE.md: `<!-- BEGIN GOC v<version> -->` / `<!-- END GOC -->` so `goc upgrade` can re-sync
  - [ ] Validated on at least three agent runtimes: Claude Code, OpenCode, and one of {Codex, Cursor, Copilot} — agent reads AGENTS.md and recognizes the deck-first mode
  - [x] CLAUDE.md sections become a "Claude-specific delta" (silent runtime via UserPromptSubmit hook) — overlap with AGENTS.md is removed; cross-link from CLAUDE.md → AGENTS.md for shared content
  - [ ] Test: in a freshly-installed repo, removing CLAUDE.md and using only AGENTS.md, an OpenCode session can still file/advance/finish a card via `goc` verbs
---

# Write AGENTS.md alongside CLAUDE.md

## Why

Sub-card of `ship-game-of-cards-as-cross-agent-cli`. The methodology framework's reach extends as far as agents read its guidance file — and CLAUDE.md is read by exactly one agent.

AGENTS.md is the convention that won. It's now stewarded by the Agentic AI Foundation under the Linux Foundation. Claude Code, OpenAI Codex, Cursor (rules), GitHub Copilot's coding agent, OpenCode, and Aider all read it. Spec-Kit's `init` writes AGENTS.md as the default; same with BMAD, Agent OS, and Ruler. Any methodology framework shipping in 2026 that writes only CLAUDE.md is voluntarily restricting itself to one runtime.

The high-leverage move: write AGENTS.md as the canonical guidance file; treat CLAUDE.md as a Claude-specific delta containing only the things that are genuinely Claude-only (the `UserPromptSubmit` silent-runtime hook, plugin-marketplace integration if any).

## What

A new template in the package data — `templates/agents_md/agents_section.md` — written/merged into the target repo's `AGENTS.md` by `goc install`. Same marker-bounded merge pattern used for CLAUDE.md so `goc upgrade` can re-sync.

Content split:

| File | Audience | What goes in it |
|---|---|---|
| `AGENTS.md` | Every agent reading the file (Claude, Codex, Cursor, Copilot, OpenCode, Aider) | Deck-first mode; what `goc new` / `goc kanban` / `goc done` do; how DoD enforcement works; Andon-cord pattern; `pull-card` semantics; cross-link to CLAUDE.md for Claude-specific behaviors |
| `CLAUDE.md` GoC section | Claude Code only | Silent runtime via UserPromptSubmit hook; the `Skill(...)` notation pointing at the 11 skills; plugin/marketplace specifics if relevant |

The shared content lives in AGENTS.md; CLAUDE.md becomes a thin "and on Claude Code, additionally:" delta.

## How

1. **Author `templates/agents_md/agents_section.md`** — agent-agnostic version of the GoC briefing. Replace `Skill(create-card)` with `goc new`. Replace "the user types something and the UserPromptSubmit hook detects work intent" with "ask the agent to file a card; it runs `goc new`."
2. **Author the slimmer `templates/claude_md/claude_section.md`** — Claude-only deltas only.
3. **Wire `goc install` to write/merge both** — same marker-bounded logic as the CLAUDE.md flow.
4. **Validation**: install on a test repo; open with OpenCode (no Claude); ask OpenCode to "file a card for X"; confirm it runs `goc new` correctly without needing CLAUDE.md.

## Why this is medium-contribution (not high)

- Bounded scope: it's authoring two markdown templates and wiring them into the install flow.
- Reversible: if the AGENTS.md text is awkward, `goc upgrade` re-syncs.
- High *reach* multiplier (one file → 6 agents) but the *implementation* is small.

## Cross-references

- Parent epic: `ship-game-of-cards-as-cross-agent-cli`
- Sibling install card: `install-command-scaffolds-repo` (consumes the AGENTS.md template alongside the CLAUDE.md template)
- AGENTS.md spec: https://agents.md (Linux Foundation)
- OpenCode native skill compat: sst/opencode reads `.claude/skills/` directly, so the `goc` verbs surface there once skills are installed

## Validation required (DoD-4 + DoD-6)

The implementation is shipped (goc commit `df473f7` in `~/Projects/game-of-cards`):

- `goc/templates/AGENTS_GOC.md` — agent-agnostic GoC briefing (no `Skill(...)` notation; uses `goc <verb>` and "ask the agent to..." phrasings).
- `goc/templates/CLAUDE_GOC.md` — slimmed to Claude-specific delta only (60% smaller; cross-links to AGENTS.md for shared briefing).
- `goc install` and `goc upgrade` write/re-sync both files with the same marker-bounded merge pattern.
- Smoke-tested on a fresh tmpdir: pre-existing AGENTS.md with user content survives both install AND upgrade re-sync.

**What needs a human session** (the two unticked DoD items):

1. **DoD-4** — Open a fresh repo with `goc install`, then drive sessions in OpenCode AND one of {Codex, Cursor, Copilot}. Confirm each agent reads AGENTS.md and recognizes the deck-first mode (asking it to "file a card for X" should produce a `goc new` invocation, not a Claude-specific `Skill(...)` call).
2. **DoD-6** — In a freshly-installed repo, `rm CLAUDE.md`, open with OpenCode (or another non-Claude runtime), and confirm a full card lifecycle (`goc new` → edit DoD → `goc done`) works end-to-end with only AGENTS.md present.

I cannot drive non-Claude runtimes from this Claude Code session, so the gate is raised to `session` until a human runs the cross-runtime check.

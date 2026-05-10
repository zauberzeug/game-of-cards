---
title: write-agentsmd-alongside-claudemd
summary: "AGENTS.md is the Linux-Foundation-stewarded shared-substrate convention read by Codex, Cursor, Copilot's coding agent, OpenCode, and Aider. Claude Code does NOT read AGENTS.md by default — it reads CLAUDE.md, and the official guidance is to either import AGENTS.md into CLAUDE.md via `@AGENTS.md` syntax or symlink CLAUDE.md → AGENTS.md. `goc install` should write/merge an `AGENTS.md` block (so the methodology is visible to the five non-Claude agent runtimes) AND ensure CLAUDE.md actually pulls AGENTS.md content into Claude's context — today's slimmed `CLAUDE_GOC.md` uses a plain markdown link `[AGENTS.md](AGENTS.md)`, which does not import. Same marker-bounded merge pattern as CLAUDE.md (so `goc upgrade` can re-sync without clobbering user content)."
status: open
stage: null
contribution: medium
created: 2026-05-03
closed_at: null
human_gate: session
advances:
  - ship-game-of-cards-as-cross-agent-cli
advanced_by:
  - claude-md-template-must-import-agents-md-content
  - kickoff-asks-where-goc-briefing-lives
  - shrink-root-guidance-files-by-moving-content-into-skills
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

AGENTS.md is the convention stewarded by the Agentic AI Foundation under the Linux Foundation. OpenAI Codex, Cursor (rules), GitHub Copilot's coding agent, OpenCode, and Aider all read it directly. **Claude Code does NOT** — its docs say "Claude Code reads `CLAUDE.md`, not `AGENTS.md`" and recommend either an `@AGENTS.md` import in CLAUDE.md or a `ln -s AGENTS.md CLAUDE.md` symlink to bridge the two. Spec-Kit's `init` writes AGENTS.md as the default; same with BMAD, Agent OS, and Ruler. Any methodology framework shipping in 2026 that writes only CLAUDE.md is voluntarily restricting itself to one runtime.

The high-leverage move: write AGENTS.md as the canonical guidance file (read by 5 non-Claude runtimes directly), and ensure CLAUDE.md *actually imports* AGENTS.md content — not just links to it — so Claude Code sees the same briefing without duplication. Today's slimmed `CLAUDE_GOC.md` template misses this: it uses a plain markdown link, which Claude Code does not follow as an import. Bug filed separately.

## What

A new template in the package data — `templates/agents_md/agents_section.md` — written/merged into the target repo's `AGENTS.md` by `goc install`. Same marker-bounded merge pattern used for CLAUDE.md so `goc upgrade` can re-sync.

Content split:

| File | Audience | What goes in it |
|---|---|---|
| `AGENTS.md` | Codex, Cursor, Copilot, OpenCode, Aider directly; Claude Code via `@AGENTS.md` import in CLAUDE.md | Deck-first mode; what `goc new` / `goc kanban` / `goc done` do; how DoD enforcement works; Andon-cord pattern; `pull-card` semantics; cross-link to CLAUDE.md for Claude-specific behaviors |
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

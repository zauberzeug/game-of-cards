---
title: split-claude-specific-content-out-of-generic-kickoff-skill
summary: "Refactor the kickoff skill: keep `goc/templates/skills/kickoff/` host-agnostic (intro, persona dialog, scaffold `.game-of-cards/`, run goc install) and move Claude Code-specific UX flow (Bash permission grant, `/plugin install` cadence, `CLAUDE.local.md` merge prompts) into a separate `claude-kickoff` skill that the Claude plugin ships as a complement. Establishes the pattern for per-host kickoff complements (`openclaw-kickoff` later)."
status: done
stage: null
contribution: medium
created: 2026-05-09
closed_at: 2026-05-09
human_gate: none
advances:
  - provide-openclaw-plugin-for-skills-and-hooks
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [x] `goc/templates/skills/kickoff/SKILL.md` rewritten to be host-agnostic: introduces GoC, runs the persona dialog, scaffolds `.game-of-cards/` via `goc install`. No Claude Code-specific permission-prompt UX, no `/plugin install` references, no `CLAUDE.local.md` flow.
  - [x] New skill `goc/templates/skills/claude-kickoff/SKILL.md` contains the Claude Code-specific complement: Bash permission grant guidance, `/plugin install` cadence, `CLAUDE.local.md` merge prompts. References the generic kickoff skill via natural language (no `Skill(name)` jargon — that's Claude-specific too, but unavoidable inside a Claude-specific skill).
  - [x] `goc install --agents claude` includes `claude-kickoff` alongside the generic kickoff in the installed skill set; `goc install --agents codex` does not.
  - [x] Claude plugin payload (`claude-plugin/skills/`) includes both `kickoff/` and `claude-kickoff/` after pre-commit sync.
  - [x] OpenClaw plugin payload (`openclaw-plugin/skills/`) includes only the generic `kickoff/` (or its invocation-neutral port). Lists the missing OpenClaw-specific kickoff complement as a follow-up card if not authored in this work.
  - [x] `uv run goc validate` passes.
worker: {who: "claude[bot]", where: main}
---

# Split Claude-specific content out of the generic kickoff skill

## Why

The current `goc/templates/skills/kickoff/SKILL.md` mixes two concerns:

1. **Generic GoC onboarding** — introduce the methodology, ask which persona fits (solo/team/OSS-eval/agent-runtime), run preflight checks, scaffold `.game-of-cards/` via `goc install`. This content is portable across any host.

2. **Claude Code-specific UX flow** — guide the user through the Bash permission prompt for `goc:*`, explain `/plugin install` cadence, prompt for `CLAUDE.local.md` merge. This content only makes sense inside Claude Code.

Mixing them couples the kickoff skill to one host. When porting to OpenClaw (`provide-openclaw-plugin-for-skills-and-hooks`), the OpenClaw plugin needs either a forked kickoff body (drift) or a stub that omits kickoff (worse onboarding). Same problem will recur for Codex, OpenCode, or any future host.

## What

Two skills:

- **`kickoff`** (generic, ships in every harness): the methodology onboarding plus the universal preflight + scaffold. Skill body talks about the deck, the persona dialog, and `goc install` — nothing about a specific host's UX primitives.
- **`claude-kickoff`** (Claude Code-specific complement): the Bash permission prompt guidance, the `/plugin install` cadence note, the `CLAUDE.local.md` merge dialog. Body cross-refs the generic kickoff via natural language ("after the generic kickoff scaffolds `.game-of-cards/`, this skill walks the Claude Code-specific permission grant").

## Pattern this establishes

Per-host kickoff complements: `claude-kickoff`, `openclaw-kickoff` (later), `codex-kickoff` (if needed). Each ships only with its own host's harness/plugin. The generic kickoff is the substrate.

This is the same pattern already in use for `CLAUDE.md` (Claude Code-specific) vs. `AGENTS.md` (host-agnostic). Skills had drifted from that pattern; this card brings them back.

## Cross-references

- `provide-openclaw-plugin-for-skills-and-hooks` — surfaced the host-coupling during the OpenClaw porting work.
- `make-claude-md-and-agents-md-merge-opt-in-via-skill` (superseded) — earlier work that established the per-host-file pattern; this card extends it to skills.

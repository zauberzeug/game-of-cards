---
title: make-claude-md-and-agents-md-merge-opt-in-via-skill
summary: "Today `goc install` (even in its lean plugin-default mode from `claude-install-defaults-to-plugin-path`) writes/merges the GoC blocks into AGENTS.md and CLAUDE.md unconditionally. For evaluators trying GoC on a library or OSS repo, that single behavior is the most invasive thing the tool does. Make the merge opt-in: by default the plugin install ships skills only; the user (or agent on user request) calls a `Skill(game-of-cards)` (rename of today's `Skill(bootstrap)`) to extend AGENTS.md / CLAUDE.md / CLAUDE.local.md. Without that opt-in the user must address skills explicitly — which is fine for evaluation."
status: open
stage: null
contribution: medium
created: 2026-05-07
closed_at: null
human_gate: session
advances:
  - ship-game-of-cards-as-cross-agent-cli
  - support-external-game-of-cards-state-location
advanced_by:
  - rename-bootstrap-to-kickoff-as-onboarding-dialog
tags: [story, infra]
definition_of_done: |
  - [ ] Default plugin install does NOT touch AGENTS.md / CLAUDE.md / CLAUDE.local.md / pre-commit hooks; it only installs skills + hook scripts the plugin owns
  - [ ] `Skill(game-of-cards)` (renamed from `Skill(bootstrap)`) is the explicit opt-in: when invoked, it offers to extend AGENTS.md / CLAUDE.md / CLAUDE.local.md with the GoC briefing block (marker-bounded, idempotent on re-invocation)
  - [ ] Skill explains the trade-off before writing: extending the markdown means fewer skill mentions per session but adds GoC content to a tracked file (issue for OSS / library repos)
  - [ ] CLAUDE.local.md (gitignored) is offered as the non-invasive default target so evaluators get the briefing without polluting the tracked repo
  - [ ] First-run UX without the merge: user prompts agent with explicit skill mentions like "use `Skill(create-card)` to file …". Documented in README so this is a known and reasonable mode
  - [ ] Existing flow that always merges (used by repos that have already opted in) is preserved by re-running the skill; `goc upgrade` does not re-merge unless the markers are present (signal that the repo already opted in)
  - [ ] AGENTS.md / CLAUDE.md / README in this repo updated to describe the new opt-in flow
  - [ ] `uv run goc validate` passes
---

# Make CLAUDE.md and AGENTS.md merge opt-in via skill

## Why

`claude-install-defaults-to-plugin-path` (done) removed the
`.claude/skills/` and `.claude/hooks/` writes from the default
install but kept the AGENTS.md / CLAUDE.md merge. For library / OSS /
strictly-controlled projects, mutating tracked configuration files
on install remains the disqualifier — those are the files the
contributor community looks at.

The fix mirrors the same opt-in pattern: the merge becomes a
deliberate choice the user makes when they decide GoC fits their
workflow, not a side effect of installing the plugin.

## Why session-gated

Open design questions:

1. UX without the merge: how does the agent discover GoC skills
   exist on a fresh repo if CLAUDE.md isn't extended? Plugin's
   skill discovery is automatic in Claude Code; the merge is mostly
   for cross-runtime portability and as a hint to the human reader.
2. CLAUDE.local.md as default target: is it a stable enough
   convention that we can rely on it for the briefing block?
3. Should the skill detect when the user is running on a personal
   project (no remote, single contributor) vs. a shared OSS repo
   and pick a smarter default — or always ask?
4. Pre-commit hook installation (the third invasive surface) —
   separate card or fold into this one?

## Cross-references

- `claude-install-defaults-to-plugin-path` (done) — established
  plugin-as-default but kept the markdown merge
- `plugin-bootstraps-cli-and-project-state-on-first-use` (done) —
  current bootstrap skill (likely renamed to `Skill(game-of-cards)`)
- `write-agentsmd-alongside-claudemd` (open) — the AGENTS.md merge
  itself; this card changes WHEN that runs, not WHAT it writes

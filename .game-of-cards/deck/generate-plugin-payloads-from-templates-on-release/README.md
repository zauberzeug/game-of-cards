---
title: generate-plugin-payloads-from-templates-on-release
summary: "Eliminate the byte-for-byte duplication between `goc/templates/` and the various agent plugin payloads (`claude-plugin/`, future `codex-plugin/`, `openclaw-plugin/`) by generating each plugin's bundle from the templates as part of the release process. Today the duplication is enforced via a CI byte-equality check, which catches drift after the fact rather than preventing it. As Codex and OpenClaw plugins land, the duplication multiplies — three plugin trees instead of one. The right fix is generation: `goc/templates/` is the source of truth; plugin payloads are build artefacts."
status: active
stage: null
contribution: high
created: 2026-05-07
closed_at: null
human_gate: none
advances:
  - ship-game-of-cards-as-cross-agent-cli
  - support-worktrees-and-multi-agent-deck-sync
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] Release workflow generates each plugin's payload (`claude-plugin/skills/`, `claude-plugin/hooks/*.py`, future `codex-plugin/*`, `openclaw-plugin/*`) from `goc/templates/` rather than maintaining hand-edited duplicates
  - [ ] Generation step runs in CI on every tag and on every PR that touches `goc/templates/` or `claude-plugin/`, so drift fails the build at the source rather than in a downstream byte-check
  - [ ] Existing CI byte-equality assertion ('Verify plugin assets match templates byte-for-byte') is either removed or repurposed as a sanity check on the generation output
  - [ ] CLAUDE.md / AGENTS.md guidance updated: contributors edit `goc/templates/` only; plugin directories are build artefacts and may be `.gitignore`d or kept committed depending on what plugin install requires
  - [ ] Decision recorded (in this card or a child) on whether plugin directories remain checked-in (consumer install needs the bytes present in the subtree the marketplace pulls from) or move to a separate publish-only branch
  - [ ] All currently-shipping plugins (Claude today; Codex / OpenClaw when they land) consume the generator
  - [ ] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# Generate plugin payloads from templates on release

## Why

The repository carries plugin payloads in lockstep with `goc/templates/`:

| Plugin path | Mirror of |
|---|---|
| `claude-plugin/skills/` | `goc/templates/skills/` |
| `claude-plugin/hooks/deck_prompt_router.py` | `goc/templates/hooks/deck_prompt_router.py` |
| `claude-plugin/hooks/deck_session_start.py` | `goc/templates/hooks/deck_session_start.py` |

The CI step "Verify plugin assets match templates byte-for-byte"
fails the build on drift. This catches the symptom but not the
cause: a contributor still has to remember to edit both copies, and
forgetting is the default failure mode.

When Codex and OpenClaw plugins land, the duplication scales linearly
in the number of supported runtimes. Generation is the answer.

## Why session-gated

Open questions for the design session:

1. Are plugin directories checked-in build artefacts, generated on
   commit via a hook, or generated only at release time and
   published from a clean branch?
2. Does Claude Code's marketplace install require the plugin
   subtree to live in the same git ref as the source-of-truth
   templates, or can a published-plugins branch (or tag) host them?
3. How does the smoke-test plugin auto-bootstrap interact with
   generated payloads?

## Cross-references

- Existing CI byte-check in `.github/workflows/ci.yml`
- `claude-plugin/` (current Claude payload)
- `goc/templates/` (current source of truth)

## Decision

*Resolved 2026-05-09:* Lower gate to none. The implementing agent should empirically resolve Q2 (does Claude Code's marketplace install require plugin subtree to live in the same git ref as templates? — yes today, but verifiable) and Q3 (smoke-test plugin auto-bootstrap interaction). For Q1, default proposal: pre-commit hook regenerates plugin payloads from goc/templates/ and commits them, so consumer install bytes stay in same git ref while removing the manual edit-both-copies burden. Push back if this default is wrong.

*Reasoning:* Q2 and Q3 are testable by an agent, not session-only. Q1 has a reasonable default that preserves the marketplace install path. Original session gate reflected my uncertainty at filing time, not a real human-only question — agent should research and propose, human only intervenes if the proposal is wrong.

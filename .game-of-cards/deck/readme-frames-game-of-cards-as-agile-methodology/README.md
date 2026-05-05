---
title: readme-frames-game-of-cards-as-agile-methodology
summary: "Reframe README/package metadata around Game of Cards as an agile methodology, restore the \"agile in the age of AI agents\" positioning, make peer-project comparison sober and linked, and move command-heavy installation detail into a CLI reference."
status: done
stage: null
contribution: medium
created: 2026-05-04
closed_at: 2026-05-04
human_gate: none
advances: []
advanced_by: []
tags: [documentation, story]
definition_of_done: |
  - [x] README opens with Game of Cards as an agile methodology, with `goc` framed as the current implementation
  - [x] README restores the "agile in the age of AI agents" framing in visible introductory copy
  - [x] Peer-project positioning is sober, linked, and based on current external project descriptions
  - [x] Installation flow is prompt-first and does not make uv the only blessed path
  - [x] CLI-heavy installation and command reference detail lives in a separate document linked from README
  - [x] Package metadata description matches the restored positioning
  - [x] `uv run goc validate` passes
---

# README frames Game of Cards as an agile methodology

## Summary

The README currently opens by describing `goc` as "a small command-line tool".
That is accurate about today's implementation, but undersells the package:
Game of Cards is the methodology, while `goc` is the current CLI carrier for it.

The README also lost the earlier "agile in the age of AI agents" framing. Restore
that phrase in the visible lead and package metadata, then keep the rest of the
copy sober about the current alpha state.

## External positioning notes

The comparison set should be linked rather than name-dropped without context:

- Spec Kit: spec-driven development templates and bootstrapping.
- BMAD: AI-driven agile workflows and specialized agent roles.
- Agent OS: project standards and specs for AI tools.
- Ruler: instruction fan-out across agent config files.
- AGENTS.md: shared agent-facing markdown guidance format.

Game of Cards should be positioned as narrower than those projects: a repo-local
backlog lifecycle with stable card paths, gates, logs, and enforced Definition of
Done.

## Implementation

- Rewrite the README opening around the package/methodology description.
- Replace the pushy "what it is and isn't" section with a sober "where it fits"
  section and links.
- Make the first install path prompt-first, then show a short manual equivalent.
- Move install flags, upgrades, and command-reference detail into `docs/cli.md`.
- Update `pyproject.toml` description to match the restored framing.

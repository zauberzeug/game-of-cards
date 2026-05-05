---
title: build-game-of-cards-project-website
summary: "Build the Game of Cards project website as its own product surface, separate from the website illustration asset. The site should explain the methodology, show the CLI/install path, and host the session-built visual explanation without turning into a README clone."
status: open
stage: null
contribution: medium
created: 2026-05-05
closed_at: null
human_gate: session
advances: [ship-game-of-cards-as-cross-agent-cli]
advanced_by: [create-project-website-explanatory-illustration, redesign-readme-as-llm-first-marketing-page]
tags: [story, documentation]
definition_of_done: |
  - [ ] Website scope decided in a session: audience, primary pages/sections, deployment target, and content source of truth
  - [ ] Project website implemented in the repo using the chosen static-site or web-app stack
  - [ ] First viewport explains Game of Cards as a methodology/runtime, not just a CLI package
  - [ ] Site includes or reserves the final integration point for `create-project-website-explanatory-illustration`
  - [ ] Install/get-started path is accurate for current `game-of-cards` packaging
  - [ ] Site is responsive and checked on desktop and mobile
  - [ ] Build/test command is documented and passes
  - [ ] `uv run goc validate` passes
---

# Build the Game of Cards project website

## Why

The project website is a separate product surface from the README. It should make the methodology legible to people evaluating GoC, not only to people already reading the repository.

## Scope

The site should cover:

- What Game of Cards is: a deck-backed methodology runtime for agent-assisted work.
- Why cards/gates/DoD matter.
- How users install and start.
- How agent plugins and repo footprint fit once the plugin/state-location work lands.
- The explanatory illustration from `create-project-website-explanatory-illustration`.

## Session required

The site needs a design/content session before implementation. The main decisions are stack, deployment target, page structure, visual direction, and what claims belong on the marketing surface versus the CLI reference.

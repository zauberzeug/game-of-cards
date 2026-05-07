---
title: build-game-of-cards-project-website
summary: "Build the Game of Cards project website as its own product surface, separate from the website illustration asset. The site should explain the methodology, show the CLI/install path, and host the session-built visual explanation without turning into a README clone."
status: done
stage: null
contribution: medium
created: 2026-05-05
closed_at: 2026-05-05
human_gate: none
advances:
  - ship-game-of-cards-as-cross-agent-cli
advanced_by:
  - create-project-website-explanatory-illustration
  - redesign-readme-as-llm-first-marketing-page
tags: [story, documentation]
definition_of_done: |
  - [x] Website scope decided in a session: stack, visual direction, page structure, and content source of truth (resolved 2026-05-05 — see Decision)
  - [x] Custom homepage at `site/index.html` with chronicle styling (HTML + CSS + small vanilla starfield JS; no React, no Jekyll on the home page)
  - [x] First viewport (hero masthead + lede) frames Game of Cards as a methodology, not just a CLI package
  - [x] Comic from `create-project-website-explanatory-illustration` is integrated as the primary first-content figure under the lede
  - [x] Install/get-started snippet on the site is accurate for current `game-of-cards` packaging and points at canonical resources (`goc.md`, `ABOUT.md`, GitHub repo)
  - [x] `.github/workflows/pages.yml` serves `site/` at `/`, still renders `goc.md` and `ABOUT.md` as Jekyll subpages, and still mirrors raw markdown (`/index.md`, `/README.md`, `/goc.md`, `/ABOUT.md`, `/llms.txt`) for LLMs
  - [x] Site renders correctly on desktop and mobile widths — Playwright captures + Rodja visual sign-off before close
  - [x] `uv run goc validate` passes
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

## Decision

*Resolved 2026-05-05:* Hand-crafted static homepage at site/index.html (chronicle/serif aesthetic, dark navy + gold, starfield) replaces the Jekyll-rendered README at /; goc.md and ABOUT.md still render via Jekyll-cayman as subpages; raw markdown mirrors stay untouched for LLMs.

*Reasoning:* Rodja delivered a finished design (zip drop) with a distinct masthead and chronicle styling that the Jekyll-cayman default cannot express. README.md remains the LLM-readable canonical content (mirrored at /index.md, /README.md), so the visual surface and the LLM surface diverge by design.

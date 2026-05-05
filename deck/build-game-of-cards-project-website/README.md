---
title: build-game-of-cards-project-website
summary: "Render README.md at game-of-cards.com via GitHub Pages with the cayman theme. README is the single source of truth — the workflow synthesizes the Jekyll index.md from it at deploy time, so no duplicate page content is checked in."
status: active
stage: null
contribution: medium
created: 2026-05-05
closed_at: null
human_gate: none
advances: [ship-game-of-cards-as-cross-agent-cli]
advanced_by: [create-project-website-explanatory-illustration]
tags: [story, documentation]
definition_of_done: |
  - [x] Website scope decided in a session: audience, primary pages/sections, deployment target, and content source of truth
  - [x] Project website implemented in the repo using the chosen static-site or web-app stack
  - [x] First viewport explains Game of Cards as a methodology/runtime, not just a CLI package
  - [x] Site includes or reserves the final integration point for `create-project-website-explanatory-illustration`
  - [x] Install/get-started path is accurate for current `game-of-cards` packaging
  - [ ] Theme is mobile-responsive (jekyll-theme-cayman) and the deployed site checked on desktop and mobile
  - [ ] Pages workflow runs green on `workflow_dispatch` against `main`
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

*Resolved 2026-05-05:* Render README.md at game-of-cards.com via GitHub Pages, single-source from README.

*Reasoning:* Rodja owns the domain and wants README as the single source of truth for the marketing surface, with no duplicate copy to drift.

## Implementation

The website is published by `.github/workflows/pages.yml`. It does not check in a separate `index.md` — every site update flows from a README edit:

- The workflow synthesizes `_pages/index.md` from `README.md` at deploy time, dropping the leading H1 (the Jekyll layout supplies the page title).
- Repo-relative markdown links (`docs/`, `goc/`, `deck/`, `assets/`, `LICENSE`) are rewritten to absolute GitHub blob URLs so they resolve from the rendered site.
- `_pages/_config.yml` selects `jekyll-theme-cayman` (a GitHub-Pages-supported theme that is mobile-responsive by default).
- `_pages/CNAME` carries `game-of-cards.com` so GitHub auto-configures the custom domain on first deploy.
- The workflow is gated by paths `[README.md, .github/workflows/pages.yml]` plus `workflow_dispatch`, so unrelated commits don't trigger a redeploy.

### Reserved integration point for the explanatory illustration

The site mirrors README, so when the comic strip from `create-project-website-explanatory-illustration` is added to README (after its review issues are addressed — wrong domain, typos, missing legend), the next push automatically promotes it to the website. No website-side work is required to integrate it.

### Out-of-repo follow-ups

- DNS: the apex `game-of-cards.com` needs A records to GitHub Pages, or `www.game-of-cards.com` as a CNAME to `zauberzeug.github.io`. Configured at the registrar.
- Pages settings: in repo settings → Pages, set source to "GitHub Actions". One-time UI step.
- Visual verification on desktop + mobile happens after first successful deploy.

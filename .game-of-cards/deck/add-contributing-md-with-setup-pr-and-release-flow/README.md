---
title: add-contributing-md-with-setup-pr-and-release-flow
summary: "Add a small `CONTRIBUTING.md` at the repo root covering the basics a new contributor needs: environment setup (`uv sync`), the deck-based work model (Game of Cards) at a glance, coding conventions (point to CLAUDE.md), pre-commit / validate, and the single-trigger release flow (`gh workflow run release.yml -f version=X.Y.Z`). Modelled after NiceGUI's CONTRIBUTING.md but trimmed — this repo is small and most context lives in CLAUDE.md/AGENTS.md, which CONTRIBUTING.md should link to rather than duplicate."
status: done
stage: null
contribution: medium
created: "2026-05-11T04:35:23Z"
closed_at: "2026-05-11T04:36:58Z"
human_gate: none
advances: []
advanced_by: []
tags: [story, documentation]
definition_of_done: |
  - [x] `CONTRIBUTING.md` exists at repo root.
  - [x] Documents environment setup (`uv sync`, editable install, `uv run goc validate`).
  - [x] Mentions the Game-of-Cards deck-first workflow at a glance and links to AGENTS.md / `goc.md` for deeper context (no duplication).
  - [x] Documents the single-trigger release flow: `gh workflow run release.yml -f version=X.Y.Z`, recovery via `--ref vX.Y.Z`, and the "tag IS the version" + plugin-asset auto-sync invariants. Links to `release.yml` header for the long-form trail.
  - [x] Pre-commit + `goc validate` is the canonical pre-PR check.
  - [x] No content duplication: facts already in CLAUDE.md / AGENTS.md are linked, not restated.
  - [x] `uv run goc validate` passes.
worker: {who: Rodja Trappe, where: main}
---

# add-contributing-md-with-setup-pr-and-release-flow

## Why

The repo has no `CONTRIBUTING.md` today. A new contributor (human or
agent) has to read CLAUDE.md to figure out how to ship a release —
which is the right doc for *agent* context but is project-specific
prose, not a contributor onboarding page. NiceGUI's CONTRIBUTING.md is
the in-house pattern for what a public-facing contributor doc looks
like; this card adapts the structure to GoC's much smaller surface
area.

## Shape

- Keep it short. ~150 lines, not 400. The repo is a 4-file Python
  package; we don't need the NiceGUI 11-section template.
- Single-source-of-truth: facts that live in CLAUDE.md (release flow,
  plugin-asset auto-sync, version-rewrite tripwire) get a one-line
  pointer, not a copy.
- Sections to include:
  1. Project intro (one paragraph).
  2. Reporting issues.
  3. Setup (`uv sync`, editable install, key dev commands).
  4. Working with the deck (one paragraph + a link to AGENTS.md /
     `goc.md`).
  5. Coding conventions (link to CLAUDE.md; mention pre-commit).
  6. Before submitting a PR (pre-commit + `goc validate`).
  7. Submitting a PR (feature-branch workflow).
  8. Release process (the single-trigger flow — this is the user's
     explicit ask).
  9. Maintainer notes (trusted-publisher setup, etc. — link to
     `release.yml` header).

## Out of scope

- Code-of-conduct file.
- Security policy file (SECURITY.md).
- AI co-authorship guidance section (NiceGUI has a nuanced policy for
  this; we don't have a settled one and shouldn't invent it here).
- Video / tutorial section (NiceGUI ships those; GoC doesn't, yet).

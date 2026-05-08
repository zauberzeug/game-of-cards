---
title: define-personas-and-use-cases-for-game-of-cards
summary: "Write a short, concrete persona list naming who Game of Cards is for, who it is NOT for (yet), and what trade-offs each persona accepts. Most disagreement about GoC's positioning is downstream of unspoken persona mismatch — evaluators with strict commit hygiene hit invasive-install pain because libraries are not the target persona today; evaluators looking for a linear feature-planner find the autonomous loop oversized; evaluators with non-code domains miss the to-do-engine framing. The personas are the lens for prioritization and the source of copy for the README audience preamble."
status: done
stage: null
contribution: high
created: 2026-05-07
closed_at: 2026-05-08
human_gate: session
advances:
  - ship-game-of-cards-as-cross-agent-cli
  - restructure-comic-as-three-panels-and-add-audience-preamble
  - rename-bootstrap-to-kickoff-as-onboarding-dialog
advanced_by: []
tags: [story, documentation]
definition_of_done: |
  - [x] Persona list captured in a tracked doc (e.g. `ABOUT.md` section or a new `PERSONAS.md`); each persona has: short name, one-paragraph description, the workflow shape they accept (mainline vs. branches, OSS vs. internal, code-reading vs. vibe-coding), and the GoC features they need vs. don't need
  - [x] Initial persona seed list at minimum covers: (a) vibe-coder / non-developer; (b) solo developer using GoC as a personal to-do manager / linear feature-planner; (c) classical-development team with strict commit hygiene; (d) agent runtime using GoC as a generic to-do engine for non-code domains; (e) multi-human + multi-AI coordination on a shared codebase
  - [x] Each persona is mapped to a workflow recommendation (which deck-location strategy from `support-multi-branch-and-multi-user-deck-workflows`, whether the CLAUDE.md merge applies, etc.)
  - [x] Anti-personas explicitly named — "GoC is NOT for X yet" — so first-time readers of README don't try to fit a square peg
  - [x] Cross-linked from README's audience preamble (per `restructure-comic-as-three-panels-and-add-audience-preamble`)
  - [x] `uv run goc validate` passes
worker: {who: Rodja Trappe, where: main}
---

# Define personas and use cases for Game of Cards

## Why

Several open cards (README pitch, multi-user epic, SaaS exploration,
opt-in-merge) all need to know which persona they're optimizing for.
Without that lens, every design choice feels like a tradeoff between
incompatible audiences and the discussion never converges. Naming
the personas — and explicitly excluding the ones GoC does not serve
today — is the upstream unblocker.

## Why session-gated

This is a discussion + writing exercise that benefits from real-time
alignment, not implementation. Drafting personas alone risks
projecting one user's mental model. A short session with a few
prospective users (or async review) sharpens the descriptions.

## Seed personas (rough draft to refine in session)

1. **Vibe-coder** — non-developer, doesn't read code, produces apps
   via prompts. Mainline-only, accepts partial features, wants the
   AI to keep state.
2. **Solo dev with personal to-do manager** — knows code, uses GoC
   as a structured replacement for `TODO.md`. Linear card flow,
   deck stays local, no autocommit. Includes the linear feature-
   planner who wants the AI to keep context across multiple
   sessions on a multi-step feature.
3. **Classical-dev team** — branch-per-feature, strict review,
   OSS commit hygiene. Wants the deck OUT of the main repo or
   strongly opt-in.
4. **Agent runtime as to-do engine** — a chatbot or assistant that
   needs structured task management for a non-code domain.
   Cards represent things-to-do; closure may not involve a commit.
5. **Multi-agent + multi-human coordinator** — current primary use
   case for the maintainer. Mainline primary, claims visible,
   server-side agents and local humans converge on main.

## Cross-references

- `restructure-comic-as-three-panels-and-add-audience-preamble`
  (consumes this card's output)
- `support-multi-branch-and-multi-user-deck-workflows` (workflow
  recommendation per persona)
- `explore-saas-deck-hosting-with-optional-tracker-sync` (which
  persona that path serves)

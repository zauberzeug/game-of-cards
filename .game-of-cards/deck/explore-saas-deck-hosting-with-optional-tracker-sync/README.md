---
title: explore-saas-deck-hosting-with-optional-tracker-sync
summary: "Spike: hosted Game of Cards as a multi-user service. Two motivating use cases keep recurring: (1) the multi-human / multi-AI sync problem (per `support-worktrees-and-multi-agent-deck-sync`) is naturally solved by a hosted, always-in-sync deck; (2) teams that already use Jira / GitHub Issues want bidirectional sync rather than a parallel deck — that's a service feature, not a CLI feature. This card is research / business-modeling, not implementation. Output: feasibility assessment + decision on whether to pursue."
status: open
stage: null
contribution: medium
created: 2026-05-07
closed_at: null
human_gate: session
advances:
  - ship-game-of-cards-as-cross-agent-cli
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] One-page feasibility note covering: target persona (per `define-personas-and-use-cases-for-game-of-cards`), minimum viable feature set, data ownership and self-host story, pricing model sketch
  - [ ] Tracker-sync surface enumerated for at least Jira and GitHub Issues: which fields map to GoC frontmatter (`status`, `human_gate`, `contribution`, `definition_of_done`, `advances`/`advanced_by`), conflict resolution direction, auth (PAT / OAuth), webhook vs. polling
  - [ ] Decision recorded on whether to pursue, defer, or open-source the sync layer as part of `goc` itself rather than as a hosted service
  - [ ] If pursued: a follow-up epic is filed with concrete implementation cards
  - [ ] If deferred: this card transitions to `blocked` with the trigger condition for revisit
  - [ ] Cross-link from the multi-branch epic so anyone reading that epic sees the SaaS path as one of the alternatives
  - [ ] `uv run goc validate` passes
---

# Explore SaaS deck hosting with optional tracker sync

## Why

Two threads converge here:

- The multi-human / multi-AI sync problem (per the parent epic) is
  fundamentally a "shared mutable state with strong consistency"
  problem. Git on main is one solution; a hosted service that holds
  the canonical deck is another, and likely lower-friction for teams
  that don't want to push card-state commits to their code repo.
- Teams that already use Jira / GitHub Issues do not want a parallel
  deck. They want their existing tracker augmented with GoC's
  frontmatter discipline, gates, DoD enforcement, and graph
  relationships. That is a sync product, not a CLI feature, and is
  most natural as a hosted service that holds a server-side deck and
  pushes updates outward via the tracker's API.

## Why session-gated

Strategic decision, not implementation. Open questions:

1. Is this a commercial product or open-source infrastructure?
2. Does the hosted deck obviate the in-repo deck for these
   personas, or does it mirror an in-repo deck (single source of
   truth question)?
3. Auth model — PAT per user, OAuth app, organisation-level
   service account?
4. How does it interact with `evaluate-deck-as-separate-repo-or-submodule`?
   The hosted deck is essentially "deck-as-separate-repo" with the
   storage outsourced.

## Cross-references

- `integrate-github-issues-discussions-and-pull-requests` (open) —
  in-CLI GitHub integration; this card explores the alternative
  "out of CLI, in a service" path
- `support-worktrees-and-multi-agent-deck-sync` (parent epic)
- `evaluate-deck-as-separate-repo-or-submodule` (sibling alternative)
- `define-personas-and-use-cases-for-game-of-cards` (the persona
  this card serves needs to be named first)

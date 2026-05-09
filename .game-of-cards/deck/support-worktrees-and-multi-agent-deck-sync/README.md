---
title: support-worktrees-and-multi-agent-deck-sync
summary: "Epic. Today GoC assumes mainline development with the deck checked into the same repo. Three concrete failure modes need a workflow story: (1) one user with multiple worktrees can't reach the deck of the parent repo; (2) multiple humans + AIs need a sync protocol so claims and progress are visible across branches; (3) OSS / library repos cannot mix project-management commits with code history without breaking community workflow. Lemma: `.game-of-cards/` must always be in sync with all participants. This epic frames the children that explore each path."
status: open
stage: null
contribution: high
created: 2026-05-07
closed_at: null
human_gate: session
advances:
  - ship-game-of-cards-as-cross-agent-cli
advanced_by:
  - spike-worktree-auto-resolves-deck-from-main-repo
  - design-claim-protocol-with-branch-and-author-metadata
  - evaluate-deck-as-separate-repo-or-submodule
  - generate-plugin-payloads-from-templates-on-release
  - recommend-autocommit-strongly-when-deck-is-version-controlled
  - emit-advances-and-advanced-by-as-block-style-yaml-lists
tags: [epic, infra]
definition_of_done: |
  - [ ] Worktree case (one user, multiple branches) has a documented and tested workflow — covered by `spike-worktree-auto-resolves-deck-from-main-repo`
  - [ ] Multi-human / multi-AI claim protocol on shared mainline has a documented design — covered by `design-claim-protocol-with-branch-and-author-metadata`
  - [ ] Separate-repo / submodule path is evaluated and either adopted, rejected with reasons, or kept as an alternative for OSS-style projects — covered by `evaluate-deck-as-separate-repo-or-submodule`
  - [ ] README's audience preamble (per `restructure-comic-as-three-panels-and-add-audience-preamble`) names which workflow each persona should pick
  - [ ] Personas card (`define-personas-and-use-cases-for-game-of-cards`) names the workflow expectations per persona, so the picks above have a justification
  - [ ] `uv run goc validate` passes
---

# Support multi-branch and multi-user deck workflows

## Why

The current model — deck on mainline of the same repo as the code,
with autocommit on status transitions — works for solo mainline
development. It breaks in three orthogonal ways:

1. **Worktrees.** A single user with multiple worktrees on the same
   project sees a different `.game-of-cards/` per worktree (or none,
   if not checked into that branch). Claims made in one worktree
   are invisible to another.
2. **Multi-human + multi-AI.** Multiple agents + humans need to
   know which card someone is working on, on which branch, and not
   trample each other's work. The current claim mechanism pushes a
   commit to main but doesn't carry branch / author metadata.
3. **OSS / library commit hygiene.** Community contributors look at
   commits and diffs; mixing card-state churn with code commits
   makes the history unreadable and disqualifies GoC from such
   projects entirely.

The unifying invariant: **`.game-of-cards/` must always be in sync
with all participants.** Whatever the workflow, that is what makes
claims meaningful and avoids two agents working on the same card
without seeing each other's claim.

## Children

| Child | Question it answers |
|---|---|
| `spike-worktree-auto-resolves-deck-from-main-repo` | Can `goc` auto-detect that it's running in a worktree and reach into the parent repo's `.game-of-cards/`? Solves single-user-multi-thread cheaply. |
| `design-claim-protocol-with-branch-and-author-metadata` | What does a claim need to record so multi-human + multi-AI work converges on main? |
| `evaluate-deck-as-separate-repo-or-submodule` | Should the deck live outside the code repo? Solves OSS commit-history pollution. |

## Why session-gated

This is the umbrella; pulling it advances by deciding among the
children's outputs. Hold a session once at least one child has
produced a concrete design or spike result.

## Cross-references

- Active card `support-external-game-of-cards-state-location` —
  closely related; this epic may converge with or supersede it
- `surface-active-cards-in-board` (active) — visibility primitive
  that helps regardless of which workflow is picked

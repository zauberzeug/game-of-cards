---
title: support-worktrees-and-multi-agent-deck-sync
summary: "Epic. Today GoC assumes mainline development with the deck checked into the same repo. Three concrete failure modes need a workflow story: (1) one user with multiple worktrees can't reach the deck of the parent repo; (2) multiple humans + AIs need a sync protocol so claims and progress are visible across branches; (3) OSS / library repos cannot mix project-management commits with code history without breaking community workflow. Lemma: `.game-of-cards/` must always be in sync with all participants. This epic frames the children that explore each path."
status: open
stage: null
contribution: high
created: 2026-05-07
closed_at: null
human_gate: none
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
  - [x] Worktree case (one user, multiple branches) has a documented and tested workflow — covered by closed `spike-worktree-auto-resolves-deck-from-main-repo`
  - [ ] Multi-human / multi-AI claim protocol on shared mainline has a documented design and ships its implementation — covered by `design-claim-protocol-with-branch-and-author-metadata` (decision recorded; implementation pending)
  - [ ] Separate-repo / submodule path is evaluated and either adopted, rejected with reasons, or kept as an alternative for OSS-style projects — covered by `evaluate-deck-as-separate-repo-or-submodule` (decision recorded: same-repo only; trade-off write-up pending)
  - [ ] README's audience preamble (per closed `restructure-comic-as-three-panels-and-add-audience-preamble`) names which workflow each persona should pick — verify wording is in place; edit if missing
  - [ ] Personas card (closed `define-personas-and-use-cases-for-game-of-cards`) names the workflow expectations per persona — verify wording is in place; edit if missing
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

## How an agent closes this epic

Now that the children's policy decisions are recorded (see the `## Decision`
section below), this epic becomes a verification roll-up:

1. Verify both open children close cleanly. They have concrete DoD
   items remaining (closure-on-integration implementation, push retry,
   trade-off write-up). Either pull them as separate work, or fold
   their remaining work into the epic-closure pass.
2. Open the README's audience preamble and confirm the multi-human
   panel + persona descriptions point at the relevant workflow. Edit
   if the wording does not yet do so.
3. Run `uv run goc validate` and `uv run goc done support-worktrees-and-multi-agent-deck-sync`.

The epic itself contains no remaining policy decisions.

## Cross-references

- Active card `support-external-game-of-cards-state-location` —
  closely related; this epic may converge with or supersede it
- `surface-active-cards-in-board` (active) — visibility primitive
  that helps regardless of which workflow is picked

## Decision

*Resolved 2026-05-09:* Lower epic gate to none. Both open children are now agent-decidable: claim-protocol policy decisions recorded (free-form worker.who, last-writer-wins+retry, opt-in integration check); evaluate-deck decision recorded (same-repo only ships supported, alternatives documented as possible-but-unsupported). The epic's remaining DoD is verification — agents can verify children close, confirm README/personas already cover the workflows, and run `uv run goc validate`.

*Reasoning:* The session gate existed only to integrate the children's outputs. With those policy choices recorded, integration is mechanical, not judgmental — no further human input is required to pull this card.

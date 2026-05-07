---
title: spike-worktree-auto-resolves-deck-from-main-repo
summary: "Spike: when `goc` runs inside a git worktree, can it automatically detect that and resolve `.game-of-cards/` in the parent repo's working directory rather than the worktree's? This is the smallest viable experiment for the single-user-multi-thread case — one person juggling several worktrees on the same project should see ONE deck across all of them. Outcome of this spike informs whether the wider multi-human / multi-AI design (sibling cards) needs the same auto-resolution or a different mechanism."
status: done
stage: null
contribution: high
created: 2026-05-07
closed_at: 2026-05-07
human_gate: none
advances: [support-multi-branch-and-multi-user-deck-workflows]
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [x] Detect that the current working directory is a git worktree (not the primary working tree) — `git rev-parse --git-common-dir` differs from `git rev-parse --git-dir` is the standard signal
  - [x] When in a worktree, `engine.DECK_DIR` resolves to `.game-of-cards/deck/` in the *common* working tree (one level above the worktree's git dir), not the worktree's own checkout
  - [x] Behavior is opt-in via `.game-of-cards/config.yaml` (or env var) — some users may want a per-worktree deck (parallel experiments). Default for the spike is opt-in; promote to default if usage warrants it
  - [x] Verified manually: create a worktree on a side-branch, run `goc` from it, see the same open queue as on main; claim a card from the worktree, see the claim from the main checkout
  - [x] Documented in CLAUDE.md / AGENTS.md GoC blocks so agents working in worktrees know where the deck actually lives
  - [x] Edge case: multiple worktrees racing on the same card. At minimum log a warning when claim fails because card is already active; full conflict resolution belongs in `design-claim-protocol-with-branch-and-author-metadata`
  - [x] `uv run goc validate` passes
---

# Spike: worktree auto-resolves deck from main repo

## Why

`engine.py` resolves `DECK_DIR = Path.cwd() / ".game-of-cards" / "deck"`.
When the user runs `goc` from a worktree, that resolves to the
worktree's own checkout — which either has a different version of
the deck (if the side branch diverged) or no deck at all (if the
branch was forked before GoC was introduced). Either way, the user
working across several worktrees on the same project sees an
inconsistent picture.

This is the smallest test of the parent epic's lemma ("the deck
must always be in sync with all participants"): for one person
juggling worktrees, the participants are the worktrees themselves
and the solution is local — no remote, no sync protocol, just path
resolution.

## Approach

Two changes:

1. Replace the `Path.cwd()` join with a function that detects
   worktree vs. main and walks to the common working tree if needed.
   `git rev-parse --git-common-dir` vs. `git rev-parse --git-dir`
   is the standard signal.
2. Honor an opt-out (config or env) for users who want per-worktree
   decks (parallel experiments on the same project).

## Cross-references

- `support-multi-branch-and-multi-user-deck-workflows` (parent epic)
- `support-external-game-of-cards-state-location` (active) — already
  exploring deck path resolution; this spike is a focused subset

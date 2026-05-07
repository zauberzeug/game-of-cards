---
title: make-autocommit-mandatory-when-deck-is-version-controlled
summary: "Tie the autocommit behavior to whether `.game-of-cards/` is under version control. If the deck is gitignored or lives outside any git repo, autocommit is OFF (nothing to commit to anyway). If the deck is tracked, autocommit is ON and not user-configurable — because the whole point of tracking the deck is that all participants see the same state, and that invariant breaks the moment one participant chooses to defer commits. Turns today's `autocommit: true|false` config into a derived property of the deck's location."
status: open
stage: null
contribution: medium
created: 2026-05-07
closed_at: null
human_gate: session
advances:
  - support-multi-branch-and-multi-user-deck-workflows
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] `goc` detects whether `.game-of-cards/deck/` is tracked (i.e. inside a git repo AND not gitignored)
  - [ ] When deck is tracked: every status transition that today emits a commit (claim, finish, advance, etc.) commits and pushes; the behavior is not opt-out via config
  - [ ] When deck is untracked (no enclosing git repo, or `.game-of-cards/` is gitignored): no commits are emitted; the deck mutates files only
  - [ ] The previous `autocommit` config key is either removed (if no remaining valid use case) or repurposed to represent the explicit "I know what I'm doing, let me defer commits in a tracked deck" escape hatch — decision recorded in this card
  - [ ] Documented invariant: a tracked deck is a shared-state deck, and shared state requires immediate publication. The README audience preamble (per `restructure-comic-as-three-panels-and-add-audience-preamble`) names this so users picking the workflow understand the trade-off
  - [ ] Interaction with `design-claim-protocol-with-branch-and-author-metadata` clarified: claim metadata commits are part of the mandatory set
  - [ ] Interaction with `evaluate-deck-as-separate-repo-or-submodule` clarified: deck-as-separate-repo still triggers autocommit because the deck IS a tracked repo
  - [ ] `uv run goc validate` passes
---

# Make autocommit mandatory when deck is version-controlled

## Why

Autocommit is currently a config flag the user can turn off. That
made sense when the deck was always in the same repo as the code
and the user just wanted quieter `git log` output for personal
projects. With the multi-user / multi-agent / separate-repo
workflows in flight, the flag becomes a hazard: if one participant
disables autocommit, their claims and progress become invisible to
everyone else, breaking the very invariant ("`.game-of-cards/` must
always be in sync with all participants") that motivates checking
the deck in to begin with.

The cleaner rule: autocommit is a derived property, not a config
choice. The deck is either tracked (in which case shared-state
semantics apply unconditionally) or untracked (in which case there
is nothing to commit). Asking the user to pick is asking them to
break the system.

## Why session-gated

Open questions:

1. Is there any legitimate use case for "tracked deck, deferred
   commits"? E.g. squash-merging a feature branch's claim+finish
   commits into a single integration commit. If yes, the escape
   hatch survives in some form; if no, the config key disappears.
2. How does "tracked but not pushed" behave? `git commit` succeeds
   but other participants only see the change on push. Does the
   mandatory rule extend to `git push`, or only to `git commit`?
3. Migration: existing repos that explicitly set `autocommit: false`
   on tracked decks — warn, error, or silently flip?
4. Performance / merge-conflict surface: every status transition
   becomes a commit + push; on a busy mainline this guarantees
   merge conflicts on the deck. Connection to
   `design-claim-protocol-with-branch-and-author-metadata`'s
   conflict semantics is direct.

## Cross-references

- `support-multi-branch-and-multi-user-deck-workflows` (parent epic)
- `design-claim-protocol-with-branch-and-author-metadata` —
  conflict semantics this card relies on
- `evaluate-deck-as-separate-repo-or-submodule` — separate-repo is
  still tracked, so autocommit still applies

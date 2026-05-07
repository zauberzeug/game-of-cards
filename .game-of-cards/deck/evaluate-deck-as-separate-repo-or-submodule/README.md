---
title: evaluate-deck-as-separate-repo-or-submodule
summary: "Evaluate hosting `.game-of-cards/` outside the code repository — either as a sibling repo everyone clones alongside the code, as a git submodule pointed to by the code repo, or as a separately-managed remote. This addresses the OSS / library case where mixing project-management commits with the code commit history is a non-starter. Output: a recommendation with trade-offs, not necessarily an implementation."
status: open
stage: null
contribution: medium
created: 2026-05-07
closed_at: null
human_gate: session
advances: [support-multi-branch-and-multi-user-deck-workflows]
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] Trade-off matrix written: same-repo (today), sibling-repo, submodule, hosted SaaS — covering: setup cost per consumer, OSS commit-history cleanliness, claim/sync semantics, multi-agent coordination, offline behavior
  - [ ] For each option, identify which persona (per `define-personas-and-use-cases-for-game-of-cards`) it serves
  - [ ] Decision recorded: which options ship as supported configurations and which are documented as "possible but unsupported"
  - [ ] If submodule is recommended for any persona: prototype that the worktree spike (`spike-worktree-auto-resolves-deck-from-main-repo`) generalizes — i.e. `goc` finds the deck regardless of whether it's in-tree, in a submodule, or at a sibling path
  - [ ] If sibling-repo is recommended: document the discovery mechanism (config file at `.game-of-cards.toml` in the code repo pointing to the deck repo path or remote)
  - [ ] Connection to SaaS path explored: hosted multi-user GoC (per `explore-saas-deck-hosting-with-optional-tracker-sync`) is the natural extension of "deck lives elsewhere"
  - [ ] `uv run goc validate` passes
---

# Evaluate deck as separate repo or submodule

## Why

Keeping the deck inside the code repo conflicts with OSS / library
commit hygiene. Community contributors look at commits and diffs;
mixing card-state churn with code commits makes the history
unreadable and makes the tool a hard sell for projects whose code
history is part of the contract with their users.

This card is the alternative path to
`design-claim-protocol-with-branch-and-author-metadata`. Both can
co-exist: the protocol is for shops that keep the deck in-repo on
main; this card explores the option for shops that cannot.

## Trade-off seeds

| Option | Pro | Con |
|---|---|---|
| Same repo (today) | Zero setup overhead | Commit-history pollution; OSS contributors see card noise |
| Sibling repo | Clean code history; deck has its own log | Two clones to keep in sync; agents need a path resolver |
| Git submodule | Versioned link from code → deck commit | Submodules are friction; many devs avoid them |
| Hosted SaaS | Multi-user out of the box; tracker sync | Not OSS-friendly; depends on `explore-saas-deck-hosting-…` |

## Cross-references

- `support-multi-branch-and-multi-user-deck-workflows` (parent epic)
- `explore-saas-deck-hosting-with-optional-tracker-sync` (sibling)
- `support-external-game-of-cards-state-location` (active) —
  related path-resolution work that may already cover part of this

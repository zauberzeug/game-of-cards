---
title: evaluate-deck-as-separate-repo-or-submodule
summary: "Evaluate hosting `.game-of-cards/` outside the code repository — either as a sibling repo everyone clones alongside the code, as a git submodule pointed to by the code repo, or as a separately-managed remote. This addresses the OSS / library case where mixing project-management commits with the code commit history is a non-starter. Output: a recommendation with trade-offs, not necessarily an implementation."
status: active
stage: null
contribution: medium
created: 2026-05-07
closed_at: null
human_gate: none
advances:
  - support-worktrees-and-multi-agent-deck-sync
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [x] Decision recorded: only same-repo ships as supported; sibling-repo, submodule, and hosted SaaS are 'possible but unsupported'. See `## Decision` section.
  - [ ] Trade-off write-up added to README (or a docs page linked from it): same-repo (today), sibling-repo, submodule, hosted SaaS — covering setup cost, OSS commit-history cleanliness, claim/sync semantics, offline behavior. Conclude with "we ship same-repo; the others are documented unsupported configurations".
  - [ ] For each rejected option, name which persona (per closed `define-personas-and-use-cases-for-game-of-cards`) it would have served and explain why that persona is being deferred (not abandoned).
  - [ ] Connection to SaaS path noted: hosted multi-user GoC (per `explore-saas-deck-hosting-with-optional-tracker-sync`) is the natural extension of "deck lives elsewhere"; cross-link the two.
  - [ ] OSS-contributor commit-history concern surfaced into a follow-up card (or explicitly rolled into `explore-saas-deck-hosting-with-optional-tracker-sync` / `support-external-game-of-cards-state-location`) so the rejected concern is not lost.
  - [ ] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
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

- `support-worktrees-and-multi-agent-deck-sync` (parent epic)
- `explore-saas-deck-hosting-with-optional-tracker-sync` (sibling)
- `support-external-game-of-cards-state-location` (active) —
  related path-resolution work that may already cover part of this

## Decision

*Resolved 2026-05-09:* Same-repo (deck on mainline of the code repo) is the only configuration that ships as supported. Sibling-repo, submodule, and hosted SaaS are documented as 'possible but unsupported' — users can wire them up themselves, but GoC commits to the same-repo experience.

*Reasoning:* Each alternative adds substantial path-resolution and discovery code for a persona (OSS contributor base) that is not yet validated. The active epic `support-external-game-of-cards-state-location` already explores deck-path indirection; better to let that mature than ship a half-supported sibling-repo discovery now. Submodule (UX friction) and hosted SaaS (own epic — `explore-saas-deck-hosting-with-optional-tracker-sync`) are deferred. Reconsider when an OSS user actually asks.

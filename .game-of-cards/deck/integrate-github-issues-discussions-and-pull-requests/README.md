---
title: integrate-github-issues-discussions-and-pull-requests
summary: "Hold a deep design session for GitHub compatibility across issues, discussions, and pull requests. This should not be pulled as a normal implementation card until the session decides source of truth, sync direction, conflict handling, auth model, and how GitHub artifacts relate to cards, gates, and closure."
status: open
stage: null
contribution: high
created: 2026-05-04
closed_at: null
human_gate: session
advances:
  - ship-game-of-cards-as-cross-agent-cli
advanced_by: []
tags: [story, infra, api-contract]
definition_of_done: |
  - [ ] Source-of-truth and sync-direction policy accepted for issues, discussions, and PRs
  - [ ] Card schema can store stable external references without breaking validation or old cards
  - [ ] CLI can link/unlink/list GitHub references for a card
  - [ ] CLI can import at least one GitHub artifact type into a new card with source URL and useful context preserved
  - [ ] PR integration can associate a PR with one or more cards through an explicit, documented mechanism
  - [ ] Discussion integration has a documented relationship to `human_gate: decision/session`
  - [ ] Tests cover the integration with mocked GitHub/`gh` responses and no network dependency
  - [ ] Docs explain the boundary between GitHub artifacts and GoC cards, including what does and does not sync automatically
  - [ ] `uv run goc validate` passes
---

# Design GitHub issues, discussions, and pull request compatibility

## Why

People outside an agent session naturally report bugs, ask design questions, and review code in GitHub. GoC cards are the local execution contract, while GitHub issues, discussions, and PRs are collaboration surfaces. The relationship is an open question and requires a deep session before implementation.

## Scope

Artifacts in scope:

- GitHub Issues: bug reports, feature requests, external backlog items.
- GitHub Discussions: open design questions, decision records, community support.
- Pull Requests: implementation evidence, review feedback, closure linkage.

## Deep-session questions

These are the questions that decide the architecture:

- What is the source of truth: the GoC deck, GitHub, or explicit one-way bridges per artifact type?
- Should GoC create GitHub issues from cards, create cards from GitHub issues, or both?
- Should status/gate changes sync to labels/comments, or should GitHub links be reference-only at v1?
- How should PRs declare card linkage: branch name, commit trailer, PR body marker, label, or explicit `goc github link-pr` command?
- Should closing a PR close a card, merely add evidence, or never affect card state automatically?
- Should GitHub Discussions be imported as cards, linked as decision evidence, or used as the external venue for `human_gate: session` questions?
- Which auth surface is acceptable for v1: `gh` CLI, GitHub App token, GitHub Actions token, or all behind an abstraction?

## Possible shape

Start with explicit links and one-way import before attempting live bidirectional sync:

- Add a schema field such as `external_refs` with typed entries for issue, discussion, and PR URLs/IDs.
- Add commands like `goc github import issue <number>`, `goc github link <card> --issue <number>`, and `goc github refs <card>`.
- Treat GitHub labels/comments as optional projections, not canonical state.
- Use PR linkage as closure evidence, not automatic closure, until the workflow has enough invariants to avoid accidental `done`.
- Let discussions serve as decision/session evidence: a discussion can explain why a gate is raised or record the thread that lowered it.

The design should be conservative about automatic sync. The deck's value is that status, gate, and DoD are explicit contracts; GitHub compatibility should not weaken that.

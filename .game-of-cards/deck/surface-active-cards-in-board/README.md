---
title: surface-active-cards-in-board
summary: "Make active cards impossible to miss when agents choose autonomous work: board, status, and default queue views must agree about active cards so parallel sessions do not collide."
status: done
stage: null
contribution: medium
created: 2026-05-04
closed_at: 2026-05-04
human_gate: none
advances: [ship-game-of-cards-as-cross-agent-cli]
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] `goc --board` shows active cards in the ACTIVE column whenever `goc --status active` returns cards; the two commands agree on titles in a mixed open/active deck
  - [x] The default `goc` / `goc --status open` queue view surfaces a concise active-card warning or summary when active cards exist but are not included in the open list
  - [x] `goc --status all` remains a reliable full-deck view and documents/labels active cards clearly enough for parallel agents to avoid claimed work
  - [x] Agent-facing guidance for choosing autonomous work tells agents to check active cards explicitly before recommending or claiming a new card
  - [x] Tests cover board rendering and default queue rendering for a deck with at least one open card and one active card
  - [x] Smoke test in this repo: with an active card present (`surface-active-cards-in-board`; original repro card `install-codex-harness` is now done), `uv run goc --board`, `uv run goc --status active`, and the default queue make the active card visible or explicitly accounted for
---

# Surface Active Cards in Board

## Why

Parallel GoC sessions rely on `status: active` as the soft lock. During a
manual queue scan, `goc --status active` correctly showed
`install-codex-harness` as active, but `goc --board` rendered an empty ACTIVE
column and the default queue did not make the active card visible.

That is a coordination hazard: an agent choosing autonomous work can miss work
already claimed by another session and recommend adjacent or conflicting cards.

## What

Make active-card visibility consistent across the views agents naturally use
when choosing work. The board should faithfully render active cards, and views
that intentionally filter to open cards should still warn that active cards
exist outside the current filter.

## Pointers

- Repro observed 2026-05-04: `uv run goc --status active` showed
  `install-codex-harness`; `uv run goc --board` showed an empty ACTIVE column.
- Related workflow risk: recommending `install-claude-harness` or the parent
  `multi-agent-shim-which-agents-at-v1` while `install-codex-harness` is active
  can create unnecessary harness-work collisions.

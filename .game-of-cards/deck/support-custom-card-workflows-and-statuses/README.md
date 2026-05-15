---
title: support-custom-card-workflows-and-statuses
summary: "Allow projects to add more valid `status` and `stage` values while preserving queue safety, terminal-state invariants, DoD enforcement, and board rendering. The user decision is that extension should happen through valid enum expansion; the remaining session work is defining the required semantics for custom status values."
status: open
stage: null
contribution: high
created: 2026-05-04
closed_at: null
human_gate: session
advances:
  - ship-game-of-cards-as-cross-agent-cli
advanced_by:
  - support-custom-frontmatter-fields-with-enum-and-required-when-rules
tags: [story, infra, api-contract]
definition_of_done: |
  - [ ] Config/schema design supports project-defined additional valid `status` values
  - [ ] Config/schema design supports project-defined additional valid `stage` values
  - [ ] Custom status definitions declare semantics required by GoC: pickability, terminal behavior, board column, and allowed closure path
  - [ ] Custom stage definitions declare ordering/range behavior for filters and board display
  - [ ] Validator rejects cards using undeclared custom values and rejects incomplete custom workflow definitions
  - [ ] `goc status`, queue filters, board view, value sorting, and `goc validate` understand custom values
  - [ ] NiceGUI-style example values are documented as a concrete fixture once the target values are known
  - [ ] Tests cover custom status values, custom stage values, invalid definitions, filtering, board rendering, and transition enforcement
  - [ ] `uv run goc validate` passes
---

# Support custom status and stage values

## Why

The current schema intentionally keeps lifecycle state small: `open`, `active`, `blocked`, `done`, `disproved`, `superseded`, plus `human_gate` and optional `stage`. That makes autonomous work safe, but it is too rigid for consuming projects that need domain-specific status or maturity values.

The clarified direction is to allow projects to add more valid `status` and `stage` values. This needs care because status is not only display vocabulary; it controls queue pickability, terminal-state protection, and DoD enforcement.

## Session questions

These need answers before implementation:

- What are the concrete NiceGUI-style status and stage values we should use as fixtures?
- Can custom status values be terminal, or must terminal states remain the fixed built-ins?
- Can custom status values be pickable by autonomous agents, or must they map back to `open`/`active`/`blocked` semantics?
- Do project-defined stage values need ordering, ranges, or only validation/display?
- Should custom values be global project config only, or can individual card families opt into different vocabularies?
- Which behavior must remain non-customizable for autonomous safety?

## Possible shape

Prefer explicit enum extension with required semantics:

- Add project-local config for additional `status` values.
- Add project-local config for additional `stage` values.
- Require every custom status to declare the lifecycle semantics GoC relies on.
- Keep base built-in values valid everywhere for portability.
- Provide NiceGUI-style example values once the target vocabulary is known.

This keeps the methodology portable while allowing projects to express local process detail.

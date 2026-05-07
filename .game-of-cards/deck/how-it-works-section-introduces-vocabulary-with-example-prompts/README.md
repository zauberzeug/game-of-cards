---
title: how-it-works-section-introduces-vocabulary-with-example-prompts
summary: "Close the \"How it works\" section with concrete prompt examples that introduce the GoC vocabulary (cards, deck, skills, gates, advance/finish) so first-time readers know what to actually say to their agent."
status: done
stage: null
contribution: medium
created: 2026-05-05
closed_at: 2026-05-05
human_gate: none
advances: []
advanced_by: []
tags: [story, documentation]
definition_of_done: |
  - [x] "How it works" section ends with a small block of example prompts the user can copy-paste to their LLM
  - [x] Examples cover the core vocabulary in plain English: filing a card, autonomous loop / pulling, surfacing decision-gated cards, editing a card's DoD, extending the deck, finishing
  - [x] Each example prompt is paired with the GoC term(s) it exercises so readers connect intent → vocabulary
  - [x] Visual style is intentional: utterances render as italic sans-serif chips with curly quotes (distinct from `.code-block` mono); no orphaned classes left behind
  - [x] Rendered locally and approved by Rodja before close
---

# how-it-works-section-introduces-vocabulary-with-example-prompts

The current "How it works" body explains the model (cards / skills / goc /
deck) in prose, but a first-time reader still doesn't know **what to type**.
The section should close with a handful of natural-language example prompts
the user can say to their coding agent — each one quietly anchoring a piece
of GoC vocabulary so the terms become memorable through use, not definition.

Examples should feel like things a real user would say (not engineered
commands), and span the lifecycle:

- filing a new card from intent ("create a card for…")
- claiming / starting work ("work on X" / "drain the queue")
- raising a decision (parked card, human gate)
- closing / finishing
- inspecting state ("what's open?" / "show me the board")

The vocabulary callouts (card, deck, skill, gate, advance, finish, pull)
should be light — a one-line legend or inline italics — not a glossary.

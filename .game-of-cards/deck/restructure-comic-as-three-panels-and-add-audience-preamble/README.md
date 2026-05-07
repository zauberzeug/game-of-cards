---
title: restructure-comic-as-three-panels-and-add-audience-preamble
summary: "Pull installation out of the explanatory comic (3 panels read cleaner than 4) and add a short audience-targeting preamble plus a 'it's just a to-do manager' punchline ABOVE the comic. Reorders the README so a first-time reader builds a mental model BEFORE seeing install instructions; install-first ordering reads back-to-front."
status: done
stage: null
contribution: medium
created: 2026-05-07
closed_at: 2026-05-07
human_gate: none
advances:
  - ship-game-of-cards-as-cross-agent-cli
advanced_by:
  - define-personas-and-use-cases-for-game-of-cards
tags: [story, documentation]
definition_of_done: |
  - [x] Comic asset reduced to 3 panels — the install panel is removed; remaining panels carry the cards-and-autonomy story
  - [x] README opens with an audience preamble that names who this is for and who it is NOT for yet, grounded in the persona list from `define-personas-and-use-cases-for-game-of-cards`
  - [x] Preamble closes with the "it's just a to-do manager — the rest is automation around it" framing so readers cannot mis-position the tool
  - [x] Ordering: preamble → comic → "how it works" → install. Install does not appear until the reader has the mental model
  - [x] Audience copy aligns with persona names from the personas card (soft-block on that card if names need to match)
  - [x] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# Restructure comic as three panels and add audience preamble

## Why

The current comic includes an install panel; install is uninteresting
until the reader is bought in to the concept. Three panels carrying
the core story (cards exist → AI works on them autonomously → human
handles human-gated cards) read cleaner and let the README defer
install to a later section.

The audience preamble fixes a separate symptom: readers who don't fit
the current target audience spend energy debating fit instead of
absorbing the concept. Naming the audience up front — and naming who
it is NOT for yet — short-circuits that.

## Notes

- Audience copy depends on persona names from
  `define-personas-and-use-cases-for-game-of-cards`. File this card
  now so the work is visible; pick it up after the personas card
  has at least a draft.
- `redesign-readme-as-llm-first-marketing-page` (done) already
  moved install below the comic. This card is the next refinement,
  not a redo.

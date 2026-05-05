---
title: readme-introduces-autonomously-in-the-background-once
summary: "Bridge the explanatory comic's 'background' wording with the documented 'autonomous mode' vocabulary by introducing the joined phrase 'autonomously in the background' exactly once in README.md, in the 'Try it' section that already lists agent-prompting examples."
status: done
stage: null
contribution: low
created: 2026-05-05
closed_at: 2026-05-05
human_gate: none
advances: []
advanced_by: []
tags: [documentation, story]
definition_of_done: |
  - [x] README.md contains the exact phrase "autonomously in the background" exactly once
  - [x] The introducing sentence sits in the "Try it" section, after the user-prompt bullet list and before the "agent guidance and skills call goc behind the scenes" sentence, so it bridges on-demand prompting to autonomous-mode behavior
  - [x] No new occurrences of the phrase elsewhere in README.md or other docs (single-introduction discipline)
  - [x] `uv run goc validate` passes
---

# README introduces "autonomously in the background" once

## Why

The explanatory comic strip in `assets/game-of-cards.png` uses the
phrase *"in the background"* (panel 3: "You can work on the rest in the
background"). The methodology docs (AGENTS.md) call the same concept
*"autonomous mode"*. A reader who arrives via the comic and then opens
the README has no anchor that bridges the two terms.

This card adds one sentence to the README that contains the joined
phrase *"autonomously in the background"*, then leaves the rest of
the codebase to use either term independently. One introduction is
enough — the bridge is established, and repeated use would dilute it.

## Location

- `README.md`, the "Try it" section, between the existing user-prompt
  bullet list (currently ending with `"what's open in the deck?"`)
  and the existing sentence `"The agent guidance and skills call \`goc\`
  behind the scenes."`.

## Fix

Insert one line after the bullet list:

> They can also work autonomously in the background, draining the
> queue and raising a flag only when a decision needs you.

The sentence is short, contains the bridge phrase exactly once, and
implicitly references the Andon-cord behavior ("raising a flag") that
AGENTS.md describes formally.

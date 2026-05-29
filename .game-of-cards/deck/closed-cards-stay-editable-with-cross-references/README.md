---
title: closed-cards-stay-editable-with-cross-references
summary: "Endorse amending closed cards (README dashboard or `log.md` journal) when new evidence surfaces post-close, with a required cross-reference back from the original to the new card. Update the deck, finish-card, and card-schema skill bodies and the consumer-facing CLAUDE_GOC / AGENTS_GOC templates so the principle ships. Closure is not frozenness — the deck's durable value depends on each closed card staying as a live entry-point to the full learning thread."
status: done
stage: null
contribution: medium
created: "2026-05-17T03:36:17Z"
closed_at: "2026-05-17T08:50:31Z"
human_gate: none
advances: []
advanced_by: []
tags: [story, documentation, meta-fix]
definition_of_done: |
  - [x] `goc/templates/skills/finish-card/SKILL.md` carries an "After closure" subsection (or equivalent) endorsing post-close edits and prescribing the cross-reference format
  - [x] `goc/templates/skills/deck/SKILL.md` overview mentions closure ≠ frozenness in the operating-modes / lifecycle framing
  - [x] `goc/templates/skills/card-schema/SKILL.md` "What goes where" subsection notes that post-close amendments are valid (README cross-ref + `log.md` append)
  - [x] `goc/templates/CLAUDE_GOC.md` and `goc/templates/AGENTS_GOC.md` (consumer-shipped block) carry a one-line authoring rule on post-close cross-referencing
  - [x] `python scripts/sync_plugin_assets.py --check` passes after the template edits propagate to `.claude/`, `claude-plugin/`, `openclaw-plugin/` mirrors
  - [x] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# closed-cards-stay-editable-with-cross-references

## Problem framing

The current methodology has an implicit conflict about whether a closed
card is editable. `Skill(card-schema)` (lines ~61–82) frames `README.md`
as the **dashboard** ("rewritten in place; outdated content is replaced,
not amended below") and `log.md` as the **append-only journal** — and
doesn't condition either rule on `status`. `Skill(finish-card)` (lines
~100, 109) describes closure as the card's **final state** ("rewrite
them in place to describe the *applied* fix and final measurement"),
which reads as "after closure, the card is done." Neither skill
explicitly addresses what to do when new evidence surfaces after the
card was closed — a bug found weeks later, an assumption invalidated by
follow-up work, a successor card that reframes the original.

In practice (this is a finding from using goc), readers — human or AI —
navigate to a closed card as the entry point for "what was decided
about X." If the answer evolved later and the closed card stays mute,
the reader walks away with stale context. Forcing strict immutability
on closed cards orphans the original anchor: future readers have to
grep for forward references to discover what changed.

## Applied fix

The "closure is not frozenness" principle now ships across all four
methodology surfaces:

- `goc/templates/skills/finish-card/SKILL.md` carries an
  "After closure — closure is not frozenness" section (before the
  `Cross-references` section). It states the principle, routes
  amendments through `log.md` (append-only `## YYYY-MM-DDTHH:MM:SSZ
  — Post-close amendment` entry) and an optional `> Later evidence:`
  pointer atop the README, and pins the rule that the original
  closure entry itself is never rewritten.
- `goc/templates/skills/deck/SKILL.md` lifecycle section now includes
  a "Closure is not frozenness" paragraph after the terminal-status
  description, cross-linking to `Skill(finish-card)` "After closure".
- `goc/templates/skills/card-schema/SKILL.md` "What goes where"
  subsection has a new "Concrete consequences" bullet declaring the
  post-close amendment a valid `log.md` append, with the same README
  pointer guidance.
- `goc/templates/CLAUDE_GOC.md` and `goc/templates/AGENTS_GOC.md`
  consumer-shipped blocks both end with a one-line authoring rule
  pointing at the finish-card "After closure" section.
- `python scripts/sync_plugin_assets.py` propagated the template
  edits to `.claude/skills/`, `claude-plugin/skills/`, and
  `openclaw-plugin/skills/`; the local dogfood `AGENTS.md` marker
  block was hand-mirrored.

No CLI behavior changed — `goc` already permits editing files in any
directory regardless of card status. The work was documentation-only.

## Why it matters

The deck is supposed to be the durable record of *what was learned*,
not just *what shipped*. If closure freezes the dashboard, the
original card becomes a dead reference the moment the next finding
lands — and the kanban accumulates orphan threads. Cross-referencing
from the original keeps it as a navigable anchor and preserves the
narrative continuity that lets a cold reader (weeks later, agent or
human) reconstruct "what we know about X" without doing a forward
graph traversal.

This is paired with the existing log.md / README contract — log.md
journal stays append-only; the new rule is the post-close amendment
*is* a valid append.

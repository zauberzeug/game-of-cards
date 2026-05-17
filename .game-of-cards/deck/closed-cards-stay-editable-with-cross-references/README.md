---
title: closed-cards-stay-editable-with-cross-references
summary: Endorse amending closed cards (README dashboard or `log.md` journal) when new evidence surfaces post-close, with a required cross-reference back from the original to the new card. Update the deck, finish-card, and card-schema skill bodies and the consumer-facing CLAUDE_GOC / AGENTS_GOC templates so the principle ships. Closure is not frozenness — the deck's durable value depends on each closed card staying as a live entry-point to the full learning thread.
status: open
stage: null
contribution: medium
created: "2026-05-17T03:36:17Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [story, documentation, meta-fix]
definition_of_done: |
  - [ ] `goc/templates/skills/finish-card/SKILL.md` carries an "After closure" subsection (or equivalent) endorsing post-close edits and prescribing the cross-reference format
  - [ ] `goc/templates/skills/deck/SKILL.md` overview mentions closure ≠ frozenness in the operating-modes / lifecycle framing
  - [ ] `goc/templates/skills/card-schema/SKILL.md` "What goes where" subsection notes that post-close amendments are valid (README cross-ref + `log.md` append)
  - [ ] `goc/templates/CLAUDE_GOC.md` and `goc/templates/AGENTS_GOC.md` (consumer-shipped block) carry a one-line authoring rule on post-close cross-referencing
  - [ ] `python scripts/sync_plugin_assets.py --check` passes after the template edits propagate to `.claude/`, `claude-plugin/`, `openclaw-plugin/` mirrors
  - [ ] `uv run goc validate` passes
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

## Current state

- `goc/templates/skills/card-schema/SKILL.md:61` — "What goes where"
  subsection treats the README/`log.md` split as universal, no
  closed-card carve-out.
- `goc/templates/skills/finish-card/SKILL.md:100` — closure language
  ("dashboard showing the card's final state") implies frozenness.
- `goc/templates/skills/deck/SKILL.md` — overview does not mention
  the lifecycle rule.
- `goc/templates/CLAUDE_GOC.md` / `goc/templates/AGENTS_GOC.md` — the
  consumer-shipped marker block has authoring rules but nothing on
  post-close amendments.

No CLI behavior is in scope — `goc` already permits editing files in
any directory regardless of card status. This is documentation-only.

## Fix proposal

State the principle once and reference-link from the other surfaces.
Canonical wording:

> Closure is not frozenness. When new evidence surfaces after a card
> closes — a bug found later, an assumption invalidated, a follow-up
> that reframes the original — file a new card for the new work AND
> amend the closed card to point readers forward. Treat the amendment
> as additive (a back-reference, a corrected assumption); do not
> rewrite the original closure entry itself. The deck is the durable
> record of what was learned, not just what shipped, so the closed
> card stays as the live entry-point to the full thread.

Suggested cross-reference format (one line, dated, appended to
`log.md` AND surfaced at the top of the README body if material):

```
[YYYY-MM-DD] Post-close amendment: superseded by [`<new-card-title>`](../<new-card-title>/) — <one-line reason>.
```

`log.md` is append-only as always — the post-close entry is a new line,
not a rewrite. The README may add a single "Later evidence" pointer
near the top so cold readers see it before reading the closure
narrative.

Specific edits:
1. `goc/templates/skills/finish-card/SKILL.md` — add an "After closure"
   subsection at the end, with the principle and the cross-ref format.
2. `goc/templates/skills/deck/SKILL.md` — one line in the lifecycle /
   operating-modes overview that closure ≠ frozen.
3. `goc/templates/skills/card-schema/SKILL.md` — extend "What goes
   where" with a row or note on post-close amendments.
4. `goc/templates/CLAUDE_GOC.md` and `goc/templates/AGENTS_GOC.md` —
   one-line authoring rule (paired with the existing "English only,"
   "no direct quotes" rules) on cross-referencing post-close evidence.
5. Run `python scripts/sync_plugin_assets.py` so `.claude/skills/`,
   `claude-plugin/skills/`, and `openclaw-plugin/skills/` mirrors stay
   byte-for-byte with the templates (CI tripwire enforces parity).

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

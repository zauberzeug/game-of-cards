---
title: deck-skill-board-legend-misstates-pullability-of-dependency-flagged-cards
summary: The `deck` skill's `goc --board` legend tells agents a `⏳` means "not ready to pull" and "No ⏳ ⇒ pullable", but the engine paints `⏳` on three axes — only two of which hide a card from the pull queue. A dependency-flagged card carries `⏳` yet is fully pullable, and the legend omits the `human_gate` axis entirely, so an agent reading the legend skips cards the scheduler would hand it next and misjudges which parked cards are pullable.
status: done
stage: null
contribution: high
created: "2026-06-18T04:47:07Z"
closed_at: "2026-06-18T04:50:26Z"
human_gate: none
advances: []
advanced_by: []
tags: [documentation]
definition_of_done: |
  - [x] `goc/templates/skills/deck/SKILL.md` `goc --board` legend row rewritten to describe all three `⏳` axes and to distinguish queue-hiding axes (`human_gate != none`, active impediment overlay) from the advisory-only dependency-block (still pullable)
  - [x] The misleading biconditional "No `⏳` ⇒ pullable" removed/corrected
  - [x] Plugin/consumer mirrors regenerated via the sync hook so `.claude`, `.codex`, and plugin copies match the template
  - [x] Regression guard added to `tests/test_guidance_accuracy.py` asserting the deck board legend names the `human_gate` axis and does not claim a dependency-block makes a card unpullable
  - [x] `uv run python -m unittest discover -s tests` passes; `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# deck-skill-board-legend-misstates-pullability-of-dependency-flagged-cards

## What's wrong

The `deck` skill's "Daily CLI verbs" table documents the board glyph at
`goc/templates/skills/deck/SKILL.md:131`:

> `| goc --board | Multi-column kanban view. A ⏳ after an open card's [contribution] marker means "not ready to pull" — either a derived dependency-block (a non-terminal advanced_by prereq) or an active impediment overlay (waiting_on / future waiting_until). No ⏳ ⇒ pullable. |`

This legend asserts a biconditional — `⏳` ⇒ not-pullable, and "No `⏳` ⇒
pullable" — and lists two causes. Both are wrong against the engine.

The board cell renderer paints `⏳` on **three** axes
(`goc/engine.py:2818-2822`):

```python
not_ready = live and (
    t.human_gate != "none"
    or (t.status == "open" and dependency_blocked(t, by_title))
    or waiting_impedes(t)
)
```

But the actual pull predicate `card_is_ready`
(`goc/engine.py:2079-2104`, consumed by `--ready` / `pull-card` /
`next-card`) deliberately **ignores `dependency_blocked`**:

> "Non-terminal `advanced_by` prereqs do NOT block readiness ... See
> `dependency_blockers` / `dependency_blocked`, which remain as advisory
> display only."

So:

1. A **dependency-blocked** open card (`human_gate: none`, no
   `waiting_on`, but an open `advanced_by` prereq) carries `⏳` yet **is
   fully pullable**. The legend's "No `⏳` ⇒ pullable" is a false
   biconditional: a `⏳`-flagged card can still be the next thing the
   scheduler hands you. An agent that trusts the legend skips it.
2. The legend omits the **`human_gate != none`** cause of `⏳`
   entirely — yet that axis was added to the engine board predicate by
   the closed card `board-omits-pull-blocking-marker-for-human-gate-parked-cards`.
   The skill legend was never updated to match.

The board comment itself states the intent at `engine.py:2815-2817`:
`dependency_blocked` "stays included as an advisory 'has an open prereq'
hint (it does not hide the card from the queue, but the board flags it)."

## Why it matters

The `deck` skill is the front-door methodology briefing loaded by agents
each session. This legend is the one place that explains what the board
glyph means. An autonomous puller that internalizes "⏳ ⇒ skip it" will
pass over dependency-flagged cards that are the highest-leverage ready
work, and will misjudge gated cards as pullable because the legend never
mentions the `human_gate` axis. This is documentation contradicting the
authoritative engine behavior — `contribution: high`, `tags: [documentation]`.

## Reachability path

This is a documentation surface, not a code path: the offending text
ships in `goc/templates/skills/deck/SKILL.md` and is mirrored verbatim
into `.claude/skills/deck/SKILL.md`, `.codex/skills/deck/SKILL.md`, and
the plugin payloads. Every consumer of GoC reads this legend; every agent
session that loads `Skill(deck)` sees it. The contradiction is
demonstrable by reading the engine predicate (`card_is_ready` returns
`True` for a dependency-blocked, gate-free, unimpeded open card while
`render_board` paints `⏳` on it).

## Fix

Rewrite the `goc --board` legend row in
`goc/templates/skills/deck/SKILL.md` to mirror the engine's three axes,
distinguishing the two queue-hiding axes from the advisory-only
dependency-block. Run the sync hook to regenerate the mirrors. Add a
regression guard to `tests/test_guidance_accuracy.py`.

See `reproduce.py` for the empirical demonstration.

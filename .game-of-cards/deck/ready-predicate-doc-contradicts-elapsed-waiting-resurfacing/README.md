---
title: ready-predicate-doc-contradicts-elapsed-waiting-resurfacing
summary: "The `card-schema` skill's boxed ready-to-pull predicate lists `∧ waiting_on unset` as a standalone hard conjunct, so read literally a card with `waiting_on` set can never be ready. But `waiting_impedes` resurfaces a card the moment its `waiting_until` elapses, regardless of `waiting_on` — and the skill's own prose a few lines below correctly describes that resurfacing. The formal predicate block is internally inconsistent with both the adjacent prose and the code; it should fold the two waiting signals together (`∧ not waiting_impedes`)."
status: done
stage: null
contribution: low
created: "2026-05-26T22:28:42Z"
closed_at: "2026-05-26T23:29:38Z"
human_gate: none
advances: []
advanced_by: []
tags: [documentation, api-contract]
definition_of_done: |
  - [x] MECHANICAL: the boxed ready predicate in `card-schema/SKILL.md` is corrected so it matches `waiting_impedes` — an elapsed `waiting_until` makes a card ready even when `waiting_on` is set (e.g. replace the two waiting conjuncts with `∧ not waiting_impedes(card)`, or `∧ (waiting_on unset OR waiting_until elapsed)`)
  - [x] MECHANICAL: the corrected predicate reads consistently with the prose at `SKILL.md:366-368` (no remaining internal contradiction)
  - [x] PROCESS: plugin/skill mirrors re-synced (`python scripts/sync_plugin_assets.py --check` green) since the card-schema skill body is mirrored into the plugin payloads; `uv run goc validate` clean
worker: {who: "claude[bot]", where: main}
---

# ready-predicate-doc-contradicts-elapsed-waiting-resurfacing

## Location

- Doc side: `goc/templates/skills/card-schema/SKILL.md:330-335` — the boxed
  `ready ⇔ …` predicate.
- Prose (correct) a few lines below: `SKILL.md:366-368`.
- Code side: `goc/engine.py:1596-1629` — `waiting_impedes`; consumed by
  `card_is_ready` (`goc/engine.py:1573`).

## What's broken

The formal predicate is written as a four-way AND:

```
ready ⇔ status == open
      ∧ human_gate == none
      ∧ waiting_on unset
      ∧ (waiting_until absent or in the past)
```

The third conjunct, `waiting_on unset`, is a standalone hard requirement.
Read literally, a card with `waiting_on: external` is never ready — even
after its `waiting_until` elapses. But `waiting_impedes`
(`goc/engine.py:1628-1629`) returns:

```python
# Future date hides; elapsed date resurfaces the card.
return until_date > today
```

so a card with `waiting_on` set AND an elapsed `waiting_until` is **not**
impeded — it re-enters the queue. The function's own docstring
(`goc/engine.py:1607-1609`) states this, and the skill's prose at
`SKILL.md:366-368` agrees:

> A future `waiting_until` (or a `waiting_on` reason without a date) hides
> the card … When the date passes the card re-enters the queue with no
> manual action.

So the boxed predicate contradicts both the adjacent prose and the
implementation: it treats `waiting_on` and `waiting_until` as independent
conjuncts when the code couples them (a `waiting_on` reason only impedes
while its date has not elapsed).

## Why it matters

The boxed predicate is the canonical, copy-paste definition of "ready" that
agents reuse to reason about queue membership. An agent that trusts the box
over the prose would wrongly conclude an elapsed-but-`waiting_on` card is
permanently hidden, when in fact it resurfaces (and is meant to, as an SLE
escalation signal surfaced by `validate_waiting_overlay`). Low blast radius
(prose and code are correct; only the formula is wrong), but it is a
self-contradiction inside the schema's authoritative skill.

## Fix

Rewrite the boxed predicate's two waiting conjuncts as a single condition
that mirrors `waiting_impedes` — e.g.:

```
ready ⇔ status == open
      ∧ human_gate == none
      ∧ not waiting_impedes(card)        # waiting_on with no elapsed date, OR a future bare waiting_until
```

with a one-line gloss that an elapsed `waiting_until` resurfaces the card
regardless of `waiting_on`. Re-sync the mirrored skill body.


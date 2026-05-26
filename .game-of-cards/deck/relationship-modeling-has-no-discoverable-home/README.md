---
title: relationship-modeling-has-no-discoverable-home
summary: |-
  Edge/relationship work is split across three skills with no front
  door: `create-card` owns `--advances`/`--advanced-by` at filing time,
  `advance-card` owns `goc advance`/`unadvance` as a side-note to status
  changes, and `card-schema` holds the concepts. None AUTO-INVOKEs on
  relationship-modeling phrasings ("this is part of X", "make this
  depend on Y", "should these be an edge or a tag?"). The rich reasoning
  developed recently — the value-chain identity, the edge-vs-tag fork,
  the three coordinating-card shapes, retraction as the honest
  closure-FAIL resolution — partly lives in work-cards that will close.
  Decision: do NOT add a new skill; instead make `advance-card` the
  discoverable home for relationship modeling (broaden its triggers + a
  how-to body) and consolidate the concepts in `card-schema`'s
  value-flow axis, linking rather than duplicating.
status: active
stage: null
contribution: medium
created: "2026-05-26T06:05:09Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [documentation]
definition_of_done: |
  - [ ] `advance-card`'s `description`/trigger phrasing is broadened to
        fire on relationship-modeling intents, not just status changes:
        "this is part of X", "make this depend on Y", "these are all
        about Z", "should this be an edge or a tag?", "remove this
        dependency". (It already owns `goc advance`/`unadvance`.)
  - [ ] `advance-card` body gains a "Modeling a relationship: edge vs
        tag" section covering, as a how-to: the three coordinating-card
        shapes (aggregation epic → `child.advances:[epic]`;
        govern-cluster → shared tag; never `epic.advances:[children]`),
        retraction (`goc unadvance`) as the honest resolution when an
        edge turns out false, and grouping-via-tag (pointing at the tag
        mechanism / the sibling tag card).
  - [ ] Concepts are NOT duplicated: the section links `card-schema`'s
        value-flow axis (which already carries the value-chain identity
        + closure-vs-readiness asymmetry table) and the guardrail card
        for the edge-vs-tag fork. `card-schema` gets only what's missing
        from its reference (the three-shapes taxonomy, if not already
        present), stated once.
  - [ ] No new skill is created (explicit non-goal). No change to the
        engine's edge logic. `goc validate` + plugin-asset sync stay
        green.
  - [ ] A reader who asks "should these cards be linked, and how?" lands
        in `advance-card` and gets a decision procedure, not scattered
        fragments.
worker: {who: "claude[bot]", where: main}
---

# Relationship modeling has no front door

## The gap

Linking cards is a first-class GoC operation, but the knowledge and the
verbs are scattered, and nothing fires when a user reaches for it:

| Skill | Covers | Triggers on |
|---|---|---|
| `create-card` | `--advances` / `--advanced-by` at filing | "let's do X", "fix Y" (new work) |
| `advance-card` | `goc advance` / `unadvance` (edge mutation) | status changes — edges are a *side-note* |
| `card-schema` | value-flow axis, invariants (reference) | "what does this field mean?" |

So "this card is part of the epic", "make this depend on that", "these
are all about the same thing — should they be linked?", or "should this
be an edge or a tag?" have **no front door**. `create-card` triggers on
*new work*; `advance-card` on *status*. Relationship *modeling* between
existing cards is homeless.

## Why it bites now

The recent edge investigation produced genuinely subtle operating
guidance — the value-chain identity ("X advances Y" ⇔ Y's value chain
includes X ⇔ Y not done while X open), the edge-vs-tag fork, the three
coordinating-card shapes, retraction (`goc unadvance`) as the honest way
to resolve a spurious `advanced-by-closed` FAIL, and the
closure-vs-readiness asymmetry. Much of it has landed in `card-schema`
and in work-cards — but the *how-to* an author needs ("I have two cards;
how should they relate?") isn't anywhere an author would auto-invoke.

## Decision: expand, don't add a skill

A standalone `link-cards` skill was considered and **declined**: the
concepts belong in the `card-schema` reference, and the verbs already
live in `advance-card` (`goc advance`/`unadvance`). A new skill would
add a sync/port surface (claude + codex plugin payloads, OpenClaw port)
for content that has natural existing homes.

Instead: **make `advance-card` the front door.** It already owns the
edge-mutation verbs; broaden its triggers and add a decision-procedure
body section. Keep the *concepts* single-sourced in `card-schema` and
link them.

## Boundary vs. the guardrail card

[`no-guardrail-for-canonical-epic-edge-direction`](../no-guardrail-for-canonical-epic-edge-direction/)
owns the **lint** (a `goc validate` hint for the backwards/over-edged
signature) and the **create-card authoring-time steering** + fixtures.
This card owns the **advance-card front door** (triggers + how-to) and
the **card-schema concept consolidation**. They reference each other; to
avoid double-editing `card-schema`'s fork explanation, the canonical
statement of the three-shapes fork lives wherever it lands first — this
card only fills what's missing, stated once.

## Sibling cards (soft cluster, no edges)

Grouped by prose reference, not `advances` edges — a soft thematic
cluster with no hard ordering (the case our own guidance says wants a
tag, not an edge):
[`no-guardrail-for-canonical-epic-edge-direction`](../no-guardrail-for-canonical-epic-edge-direction/),
[`unknown-tag-error-does-not-tell-you-how-to-add-a-tag`](../unknown-tag-error-does-not-tell-you-how-to-add-a-tag/).

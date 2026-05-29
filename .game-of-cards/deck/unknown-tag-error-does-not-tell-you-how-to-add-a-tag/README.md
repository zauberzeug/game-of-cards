---
title: unknown-tag-error-does-not-tell-you-how-to-add-a-tag
summary: |-
  Tags are a closed enum: `goc new --tag X`, the `--tag` filter, and
  `goc validate` all reject any tag not in `canonical_tags`. The
  mechanism to add one is real and documented in `card-schema` ("Adding
  new tags": project tags go in `.game-of-cards/canonical-tags.md`;
  shipped tags need a PR) — but it is invisible at the moment of need.
  All three "unknown tag" errors name the constraint and not the
  remedy, and they cite "SCHEMA.md" — the wrong file for the
  consuming-repo path. `create-card` says tags "must come from the
  canonical set" without linking how to add one. So an author following
  the new guardrail advice ("group a govern-cluster with a shared tag")
  does `goc new card --tag my-group`, hits "unknown tag", and dead-ends.
  Fix: make the error messages name the fix and stop mis-citing
  SCHEMA.md; add a pointer in create-card. Discoverability only — no
  `goc tag` helper (deferred).
status: done
stage: null
contribution: medium
created: "2026-05-26T06:05:09Z"
closed_at: "2026-05-26T13:33:32Z"
human_gate: none
advances: []
advanced_by: []
tags: [documentation, api-contract]
definition_of_done: |
  - [x] The three "unknown tag" error sites in `goc/engine.py`
        (validate ~997, `--tag` filter ~1464, `goc new` ~3206) name the
        remedy: project tags → add to `.game-of-cards/canonical-tags.md`
        (`canonical_tags:` block, merged by `goc validate`); a generic
        tag → PR against goc. Stop citing "SCHEMA.md" (the consuming
        path is `canonical-tags.md`, not the shipped schema).
  - [x] `create-card` skill gains a short "need a new grouping tag?"
        pointer to the `canonical-tags.md` mechanism, placed where
        `--tag` is introduced.
  - [x] Verified end-to-end: with a fresh tag added to
        `.game-of-cards/canonical-tags.md`, `goc new x --tag <newtag>`
        succeeds; without it, the error shows the remedy line.
  - [x] The error wording is consistent across all three sites (same
        remedy sentence), so a reader sees the same fix wherever they
        hit the wall.
worker: {who: "claude[bot]", where: main}
---

# The "unknown tag" error names the rule but not the fix

## Origin

Surfaced while reviewing the edge-vs-tag guidance added to
[`no-guardrail-for-canonical-epic-edge-direction`](../no-guardrail-for-canonical-epic-edge-direction/).
That card now tells authors to model a *governing* cluster (a decision
or standard-setting card and the cards it standardizes) with a **shared
tag**, not an `advances` edge. But the moment an author acts on it, they
hit a wall the methodology never explains how to climb.

## The dead-end

Tags are a closed enum. `goc validate` (`engine.py:997`), the `--tag`
filter (`engine.py:1464`), and `goc new` (`engine.py:3206`) all reject
any tag not in `canonical_tags`, with a message of the form:

```
unknown tag 'plasticity-tests' (not in SCHEMA.md canonical_tags)
```

Two problems:

1. **It names the constraint, not the remedy.** Nothing tells the
   author that project-specific tags are added in
   `.game-of-cards/canonical-tags.md` (a fenced `canonical_tags:` YAML
   block that `goc validate` merges into the enum) — the mechanism
   `card-schema` "Adding new tags" documents.
2. **It cites the wrong file.** "SCHEMA.md" points at the shipped schema
   (which needs a PR to goc), not the consuming-repo file an adopter can
   actually edit. The label sends a self-host user toward the one path
   that *doesn't* apply to them.

`create-card` compounds it: it says tags "must come from the canonical
set" but never links how to add one — and grouping is exactly when a new
tag is wanted.

## Why it matters now

The guardrail card's whole "use a tag, not an edge, for govern-clusters"
fix is only actionable if creating a tag is discoverable. Today the
faithful encoding we just told authors to use walks them straight into
an unexplained rejection. Closing this makes that advice followable.

## Scope

Discoverability only, per decision: fix the error text + add a
create-card pointer. A `goc tag add/rm` helper that edits
`canonical-tags.md` for you (operationalizing "add a grouping tag /
retire on epic close") was considered and **deferred** — not in this
card.

## Sibling cards (soft cluster, no edges)

Part of the same guidance theme, intentionally grouped by prose
reference rather than `advances` edges (a soft, no-hard-ordering
cluster — the exact case that wants a tag, not an edge):
[`no-guardrail-for-canonical-epic-edge-direction`](../no-guardrail-for-canonical-epic-edge-direction/),
[`relationship-modeling-has-no-discoverable-home`](../relationship-modeling-has-no-discoverable-home/).

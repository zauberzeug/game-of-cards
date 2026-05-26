---
title: derive-dependency-readiness-instead-of-storing-blocked-status
summary: "Compute dependency-blocking from the advances graph instead of storing it as a manual status. A card with any non-terminal `advanced_by` prereq is derived not-ready and self-clears when the last prereq closes. Surfaces in queues, board, and the pull-card readiness predicate. Replaces the warn-only STALE_BLOCKED/ORPHAN_BLOCKED model."
status: open
stage: null
contribution: medium
created: "2026-05-24T11:22:05Z"
closed_at: null
human_gate: none
advances:
  - blocked-status-conflates-dependency-external-wait-and-deferral
  - remove-blocked-from-status-enum-and-migrate-existing-cards
advanced_by: []
tags: [api-contract]
definition_of_done: |
  - [ ] A pure function (e.g. `dependency_blocked(card, by_title) -> bool`) returns True iff the card has at least one `advanced_by` prereq whose status is non-terminal; False when all prereqs are terminal or there are none.
  - [ ] `next-card` / `pull-card` readiness excludes dependency-blocked open cards (they are not "ready to pull").
  - [ ] `goc status` / table / board renders the derived dependency-block state (e.g. a marker + which prereqs remain) without reading a stored `blocked` value.
  - [ ] `STALE_BLOCKED` is reconciled: a card whose `advanced_by` are all terminal is shown ready, not warned (the warn is now structurally impossible because nothing stays `blocked` for a resolved dependency).
  - [ ] reproduce.py demonstrates: a card with an open prereq is derived-blocked; closing the prereq makes it derived-ready with no manual status flip.
  - [ ] Does NOT remove `blocked` from the status enum (that is the sibling card) — derived readiness coexists with the legacy status until then.
---

# Derive dependency-readiness from the advances graph instead of storing it

Child of [blocked-status-conflates-dependency-external-wait-and-deferral](../blocked-status-conflates-dependency-external-wait-and-deferral/)
(see the epic for the full design rationale and literature). Implements
**Decision point 2**: dependency-blocking is derived, never stored.

## What's there today

`validate_blocker_coherence` (`engine.py:1118`) already walks `advanced_by` as
the blocker set (`engine.py:1153`) but only emits advisory warnings:

- `STALE_BLOCKED` — `status: blocked` whose `advanced_by` are all terminal.
- `ORPHAN_BLOCKED` — `status: blocked` with empty `advanced_by` + `human_gate: none`.

So "this card is waiting on an upstream card" is expressed by a *manually set*
`status: blocked` that must be *manually cleared* when the prereq finishes — the
Jira anti-pattern (no auto-transition; cards get stranded). The graph already
holds the truth; the status duplicates it and drifts.

## What to build

A **computed** readiness property, not a stored field:

- `dependency_blocked(card, by_title)` → True iff any `advanced_by` prereq is
  non-terminal (`status ∉ TERMINAL_STATUSES`). The data is already loaded; this
  is a cheap lookup.
- Feed it into the ready-to-pull predicate used by `next-card` / `pull-card`
  (alongside the existing `human_gate == none` filter) so dependency-blocked
  open cards are not offered.
- Surface it in `goc status` / table / `--board` so a reader sees "blocked by:
  <remaining prereqs>" derived live, with no stored `blocked`.
- Reconcile `STALE_BLOCKED`: once dependency-block is derived, an all-terminal
  prereq set simply yields ready — the stale warning is moot. `ORPHAN_BLOCKED`
  (a body-only blocker with no edge) is folded into the impediment overlay from
  the sibling card.

## Scope boundary

This card adds the *derived* state and wires it into queues/display. It does
**not** remove `blocked` from the status enum or migrate existing cards — that
is [remove-blocked-from-status-enum-and-migrate-existing-cards](../remove-blocked-from-status-enum-and-migrate-existing-cards/),
which this card advances. The two new behaviors (derived readiness here, the
impediment overlay in the sibling) must both exist before the status is removed.

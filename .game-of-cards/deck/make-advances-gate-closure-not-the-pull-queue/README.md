---
title: make-advances-gate-closure-not-the-pull-queue
summary: |-
  Resolve the closure-vs-readiness asymmetry left open by
  `derive-dependency-readiness-…`. An `advances` edge means "should be
  done first" (lends priority + gates *closure*), NOT "must wait to
  start". But `card_is_ready` currently excludes any card with a
  non-terminal `advanced_by` prereq, so a card whose upstream merely
  *contributes* (the ~80% loose majority) is hidden from the pull queue
  until that upstream closes — the exact "autonomous worker halts on a
  cluster" friction, relocated from closure to readiness. Reassign the
  roles (the decided option): `advances` = value flow + closure gate +
  soft "should precede"; the hard "must wait to start" gate is the
  explicit impediment overlay (`waiting_on`/`waiting_until`), which now
  ships. Mechanically: drop the `dependency_blocked` line from
  `card_is_ready`; keep the derived signal as advisory display only,
  relabeled so it no longer reads as "blocked". `advanced-by-closed`
  (closure) is unchanged.
status: open
stage: null
contribution: medium
created: "2026-05-26T06:55:44Z"
closed_at: null
human_gate: none
advances:
  - blocked-status-conflates-dependency-external-wait-and-deferral
advanced_by: []
tags: [api-contract]
definition_of_done: |
  - [ ] `card_is_ready` (`engine.py:1411`) no longer excludes a card for
        having non-terminal `advanced_by` prereqs (drop the
        `dependency_blocked` branch at ~1422). Ready = `status == open`
        AND `human_gate == none` AND `not waiting_impedes`. (Legacy
        `status: blocked` stays excluded by the `status != open` check.)
  - [ ] `dependency_blocked` / `dependency_blockers` are retained as an
        **advisory display only** — the `-v` line (~1859), the `--board`
        marker, and the `--json` keys — and relabeled so they read as
        "awaiting: <prereqs> (you may start)" rather than "blocked by".
        They no longer feed the ready predicate. The `--json` `ready`
        key reflects the new predicate automatically.
  - [ ] `next-card` / `pull-card` / `--ready` now offer a card with open
        `advances` prereqs (it is a "should", not a "must"). A hard
        "must wait to start" is expressed only by the `waiting_on`
        overlay (now shipped) or — until removed — `status: blocked`.
  - [ ] `advanced-by-closed` (closure, `_run_derived_check`) is left
        unchanged — `advances` still gates *closure* per Option E.
  - [ ] `card-schema`'s value-flow axis records the final role split:
        `advances` = value flow + closure gate + soft "should precede";
        hard "must wait to start" = impediment overlay. The
        closure-vs-readiness asymmetry table is updated so the "loose →
        may start" row matches the shipped behaviour (readiness no
        longer hard-blocks on advances at all).
  - [ ] reproduce.py: a card with an open `advances` prereq appears in
        `--ready` / is pulled by next-card (with the advisory "awaiting"
        marker still shown); a card with an active `waiting_on`
        impediment is NOT offered.
  - [ ] The closed `derive-dependency-readiness-…` card gets a dated
        forward-pointer in its `log.md` to this card (resolves its
        "Open consideration"). `goc validate` + plugin-asset sync green.
---

# `advances` should gate closure, not the pull queue

## What this resolves

The decided closure-vs-readiness split, made concrete in goc's
mechanisms. Background: the closure card
[`advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose`](../advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose/)
(Option E) established that an `advances` edge carries two behaviours
that pull apart across closure vs. start-ordering:

| edge | may a card *start* before its prereq is done? | may it *close*? |
|---|---|---|
| strict | no | no |
| loose (~80%) | **yes** | no |

Closure was settled (every true edge gates closure — value-chain
identity). The *start* side was handed to the readiness work, which
shipped the blunt version: `card_is_ready` excludes **any** card with a
non-terminal `advanced_by` (`engine.py:1422`). That treats every edge as
a hard "must wait to start", hiding loose-contributor cards from the
queue until their upstream closes — the original "autonomous worker
halts on a cluster" friction, now living in readiness.

## The decision: reassign the roles (no per-edge marker)

Rather than add a strict/loose marker to the edge (rejected for closure;
considered for readiness), reassign which mechanism carries which
meaning — which also completes the blocked-status epic's three-axis
model:

| meaning | mechanism |
|---|---|
| "should be done first" (priority + soft order; gates **closure**) | `advances` / `advanced_by` edge |
| "must be done before this can **start**" (hard start-gate) | `waiting_on` / `waiting_until` impediment overlay |
| "needs a human" | `human_gate` |

So a plain `advances` edge no longer hides a card from the queue. If
work genuinely cannot start yet, that is an *impediment* — recorded
explicitly on the card via the overlay (now shipped by
[`add-waiting-overlay-with-reason-and-until-date`](../add-waiting-overlay-with-reason-and-until-date/)),
with a reason and optional return date — not inferred from a
value-contribution edge that cannot tell "must" from "should".

## Why it lands cleanly now

Both prerequisites already shipped (`derive-dependency-readiness-…` and
`add-waiting-overlay-…` are `done`), so this is a subtraction, not a
new subsystem: remove the `dependency_blocked` branch from
`card_is_ready`. The derived signal stays for *display* (so a reader
still sees "awaiting: <prereqs>"), but it stops *excluding* the card
from work. Legacy `status: blocked` remains a hard exclusion only
because a blocked card is not `open` — untouched here; its removal is
the sibling [`remove-blocked-from-status-enum-and-migrate-existing-cards`](../remove-blocked-from-status-enum-and-migrate-existing-cards/).

## Not in scope

- The closure gate (`advanced-by-closed`) — unchanged.
- Removing `blocked` from the status enum — sibling card.
- Soft *deprioritisation* of pending-advances cards in the picker (a
  "prefer prereq-clear cards but don't hide the rest" tiebreaker) is a
  possible nicety but NOT required here; GRPW value flow already biases
  upstream work higher. Filing-worthy only if the flat behaviour proves
  insufficient.

## Lineage

Resolves the "Open consideration (2026-05-26): closure vs readiness
asymmetry" recorded on the now-closed
[`derive-dependency-readiness-instead-of-storing-blocked-status`](../derive-dependency-readiness-instead-of-storing-blocked-status/).
No frontmatter edge to that closed card (lineage is forensic — it lives
here and in its `log.md` forward-pointer).

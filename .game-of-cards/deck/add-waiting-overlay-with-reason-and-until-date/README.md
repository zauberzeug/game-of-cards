---
title: add-waiting-overlay-with-reason-and-until-date
summary: "Add a stored impediment overlay for exogenous waits the dependency graph can't derive: `waiting_on` ∈ {external, resource, deferred} plus an optional `waiting_until` ISO date. A future date is a read-time guard (card hidden from queues); an elapsed date is surfaced by validate/standup. A card may be active AND impeded."
status: done
stage: null
contribution: medium
created: "2026-05-24T11:22:11Z"
closed_at: 2026-05-26T05:52:49Z
human_gate: none
advances:
  - blocked-status-conflates-dependency-external-wait-and-deferral
  - remove-blocked-from-status-enum-and-migrate-existing-cards
advanced_by: []
tags: [api-contract, documentation]
definition_of_done: |
  - [x] Schema: `waiting_on` (optional, enum {external, resource, deferred}) and `waiting_until` (optional ISO date) added to `optional_fields` in schema.yaml; the frontmatter emitter round-trips both as flat fields.
  - [x] `goc validate`: `waiting_on` must be in the enum; `waiting_until` must parse as an ISO date; `waiting_until` alone (no `waiting_on`) IS allowed and implies `deferred`.
  - [x] Read-time guard: a card with `waiting_until` in the future is excluded from `next-card` / `pull-card` readiness; when the date passes it re-enters the queue with no manual action.
  - [x] Elapsed-wait surfacing: `goc validate` flags a card whose `waiting_until` is in the past as a `WAITING_OVERDUE` SLE-escalation signal.
  - [x] A CLI affordance sets and clears the overlay (`goc wait <title> --reason external --until 2026-06-15` and `--clear`); it composes with `status` (a card may be `active` and carry `waiting_on`).
  - [x] card-schema skill documents the overlay and the three-axis model; advance-card skill documents set/clear.
  - [x] reproduce.py: a card with a future `waiting_until` is hidden from `next-card`; backdating makes it appear and surfaces `WAITING_OVERDUE`.
worker: {who: "claude[bot]", where: main}
---

# Add a typed impediment overlay (`waiting_on` + optional `waiting_until`)

Child of [blocked-status-conflates-dependency-external-wait-and-deferral](../blocked-status-conflates-dependency-external-wait-and-deferral/)
(see the epic for the full design rationale and literature). Implements
**Decision point 3**: the only *stored* part of "stuck" — exogenous waits the
graph cannot derive.

## Why a stored field (when dependency-block is derived)

Dependency-block is derivable from the `advances` graph (sibling card). But
three block-kinds have no upstream card to walk to and so cannot be computed:

- **external** — vendor, client, hardware delivery, a third party.
- **resource** — a specific person/skill unavailable.
- **deferred** — deliberately postponed (the GTD "tickler" / OmniFocus defer
  date / MS Project "Start No Earlier Than").

These need a stored flag. Per the literature (see epic), the right shape is an
*orthogonal overlay*, not a status — so a card may be `status: active` AND
`waiting_on: external` at once.

## What to build

- **Schema**: `waiting_on` (optional enum {external, resource, deferred}) and
  `waiting_until` (optional ISO date) as flat optional fields. Follow the
  flat-frontmatter convention; no nested mapping.
- **Validation**: enum membership for `waiting_on`; ISO-date parse for
  `waiting_until`. Proposed rule: `waiting_until` alone (no `waiting_on`) implies
  `deferred`.
- **Read-time guard** (no daemon — GoC is a CLI): a future `waiting_until`
  excludes the card from `next-card` / `pull-card` readiness; it reappears once
  the date is past. This is the snooze/defer-until mechanism, evaluated when a
  command runs.
- **Elapsed-wait surfacing**: `goc validate` / standup flag a past-due
  `waiting_until` (the Kanban SLE escalation — a wait that overran its expected
  return).
- **CLI**: a verb to set and clear the overlay (proposed `goc wait <title>
  --reason <r> [--until <date>]` + clear), composing with `status`.

## Scope boundary

Adds the overlay and its read-time behavior. Does **not** remove `blocked` from
the status enum or migrate existing cards — that is
[remove-blocked-from-status-enum-and-migrate-existing-cards](../remove-blocked-from-status-enum-and-migrate-existing-cards/),
which this card advances.

---
title: remove-blocked-from-the-status-enum-and-validator
summary: |-
  Decomposition of `remove-blocked-from-status-enum-…`: the breaking
  step, lands LAST and at a release boundary. Drop `blocked` from
  `status_values` + every enum consumer (transitions, the status
  command, renderers, filters), make `goc validate` reject
  `status: blocked` with a migration-pointing message, and reconcile the
  `STALE_BLOCKED`/`ORPHAN_BLOCKED` code paths. `human_gate: session`
  because it changes the frontmatter contract consumers + plugin
  payloads depend on — it must be release-coordinated, not autonomously
  pulled. `advanced_by` the migration card (can't close while any
  `blocked` card remains).
status: open
stage: null
contribution: medium
created: "2026-05-26T12:11:27Z"
closed_at: null
human_gate: session
advances:
  - remove-blocked-from-status-enum-and-migrate-existing-cards
advanced_by:
  - migrate-existing-blocked-cards-to-open-or-waiting-overlay
tags: [api-contract, documentation]
definition_of_done: |
  - [ ] `blocked` removed from `status_values` in `goc/schema.yaml`;
        every enum consumer updated — `TERMINAL_STATUSES` neighbours,
        the `goc status <t> blocked` verb (removed or repointed),
        renderers, filters, and the inlined enum in the `card-schema`
        skill body.
  - [ ] `goc validate` rejects `status: blocked` with a message naming
        the replacement (derived dependency-readiness, or `goc wait` /
        `waiting_on`).
  - [ ] `STALE_BLOCKED` / `ORPHAN_BLOCKED` code paths reconciled —
        removed or repurposed now that no card can carry `status:
        blocked`.
  - [ ] Precondition verified: no card in the deck has `status: blocked`
        (the migration sibling has closed). `goc validate` clean;
        plugin-asset sync `--check` green.
  - [ ] Breaking-change coordination: landed at/with a release boundary
        with a migration note in the release, per the project's
        breaking-change discipline (promote to a hard blocker if the
        next release widens the audience).
---

# Remove `blocked` from the status enum + validator (breaking, release-coordinated)

Decomposition of the breaking epic
[`remove-blocked-from-status-enum-and-migrate-existing-cards`](../remove-blocked-from-status-enum-and-migrate-existing-cards/).
This is the **enforced removal** — the one breaking, release-coordinated
step, deliberately split out from the safe prep so it does NOT sit in
the autonomous pull queue.

## Why human-gated

Removing an enum value changes the card-frontmatter contract that
consumers and the Claude/Codex/OpenClaw plugin payloads depend on. The
parent card's own DoD required this to "land at a release boundary, not
as silent drift." So it carries `human_gate: session`: a human
sequences it with a release and migration note. (This is exactly the
case our model says is a real coordination point, not autonomous work.)

## Why it waits on the migration

`advanced_by: [migrate-existing-blocked-cards-to-open-or-waiting-overlay]`.
Removing the value while a `blocked` card still exists would make
`goc validate` reject the repo's own deck. So the migration must close
first — a genuine closure prerequisite (the `advanced-by-closed` gate
enforces it). Note: under the shipped readiness model this edge does
*not* hide this card from the queue (advances no longer gates
readiness) — but the `human_gate: session` keeps it out of autonomous
pulls regardless, and the edge correctly blocks its *closure* until the
migration lands.

## Sequencing with the docs sibling

The docs/skills soft-deprecation
([`purge-blocked-status-from-skills-and-docs`](../purge-blocked-status-from-skills-and-docs/))
can land before this; ideally the human coordinating this removal lands
both in the same release so docs and enforcement match.

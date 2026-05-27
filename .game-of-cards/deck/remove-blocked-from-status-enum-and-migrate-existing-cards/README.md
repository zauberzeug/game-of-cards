---
title: remove-blocked-from-status-enum-and-migrate-existing-cards
summary: "Breaking change: drop `blocked` from the status enum once dependency-readiness is derived and the impediment overlay exists. Migrate existing blocked cards (dependency-waits → open; exogenous → open + waiting_on). Rewrite card-schema/advance-card/deck skills + AGENTS docs for the three-axis model. Lands last; coordinate with a release boundary."
status: open
stage: null
contribution: medium
created: "2026-05-24T11:22:14Z"
closed_at: null
human_gate: none
advances:
  - blocked-status-conflates-dependency-external-wait-and-deferral
advanced_by:
  - derive-dependency-readiness-instead-of-storing-blocked-status
  - add-waiting-overlay-with-reason-and-until-date
  - migrate-existing-blocked-cards-to-open-or-waiting-overlay
  - purge-blocked-status-from-skills-and-docs
  - remove-blocked-from-the-status-enum-and-validator
tags: [epic, api-contract, documentation]
definition_of_done: |
  - [x] Child `migrate-existing-blocked-cards-to-open-or-waiting-overlay` closed (the safe prep — reclassify the existing blocked cards; autonomous-pull-safe).
  - [x] Child `purge-blocked-status-from-skills-and-docs` closed (advance-card/card-schema/deck/AGENTS rewrite to the three-axis model + plugin sync; autonomous-pull-safe).
  - [ ] Child `remove-blocked-from-the-status-enum-and-validator` closed (the breaking enum removal; `human_gate: session`, release-coordinated, lands last).
  - [ ] After all three: no card has `status: blocked`, the enum value is gone, docs match the code, plugin mirrors are synced, and `goc validate` is clean.
---

# Remove `blocked` from the status enum and migrate existing cards

Child of [blocked-status-conflates-dependency-external-wait-and-deferral](../blocked-status-conflates-dependency-external-wait-and-deferral/)
(see the grandparent epic for the full design rationale and literature).
Implements **Decision point 1** and the migration. The two design
prerequisites have both shipped:

- [derive-dependency-readiness-instead-of-storing-blocked-status](../derive-dependency-readiness-instead-of-storing-blocked-status/)
  (done) — dependency-waits behave correctly once flipped to `open`.
- [add-waiting-overlay-with-reason-and-until-date](../add-waiting-overlay-with-reason-and-until-date/)
  (done) — exogenous blocked cards have a destination (`waiting_on`).

## Decomposed (2026-05-26) — now an aggregation epic

This card was a single monolith that jammed the autonomous pull queue:
the picker selected it (highest value), spent ~13 min, and exited
non-zero without closing — the enum-removal + full migration + doc
rewrite is too large for one bypass-permissions pull, so it failed every
run and head-blocked the queue. Decomposed into three children so the
safe work drains autonomously and the breaking step stays
release-coordinated:

| child | gate | when |
|---|---|---|
| [migrate-existing-blocked-cards-to-open-or-waiting-overlay](../migrate-existing-blocked-cards-to-open-or-waiting-overlay/) | none | now — safe, no enum change |
| [purge-blocked-status-from-skills-and-docs](../purge-blocked-status-from-skills-and-docs/) | none | now — soft-deprecation, docs lead |
| [remove-blocked-from-the-status-enum-and-validator](../remove-blocked-from-the-status-enum-and-validator/) | session | last — breaking, release-coordinated; `advanced_by` the migration child |

This card now closes when all three close (aggregation epic). The
original 7-item implementation DoD moved into the children.

Until both close, this card is derived-blocked (its `advanced_by` prereqs are
open) — which is itself a live demonstration of the model being built.

## What to build

- **Schema**: remove `blocked` from `status_values`. Status becomes
  `open → active → done/disproved/superseded`. Update `TERMINAL_STATUSES`
  consumers and every enum reference (renderers, filters, the status command,
  the card-schema skill body that inlines the enum).
- **Validation**: `goc validate` rejects `status: blocked` with a message that
  names the replacement (derived dependency-readiness, or `goc wait`).
- **Migration**: reclassify every existing `status: blocked` card —
  - has non-terminal `advanced_by` prereqs → `status: open` (derived readiness
    covers it);
  - otherwise → `status: open` + `waiting_on: <reason>` (author/migration picks
    the reason; default `external` with a review flag if ambiguous).
  Ship this as a `goc` subcommand or a documented one-shot and run it on this
  repo's own deck (there are a small number of `blocked` cards today).
- **Docs/skills**: rewrite advance-card (drop the blocked transition), card-schema
  (status enum + three-axis model), deck (lifecycle diagram), and AGENTS docs.
  Re-sync plugin mirrors.

## Why breaking, and the release note

Removing an enum value changes the frontmatter contract that consumers and the
plugin payloads depend on. Per the project's breaking-change discipline, land
this at a release boundary with a clear migration note, not as a silent drift.

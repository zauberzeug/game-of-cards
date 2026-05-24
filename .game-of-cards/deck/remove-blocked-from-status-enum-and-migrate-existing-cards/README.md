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
tags: [api-contract, documentation]
definition_of_done: |
  - [ ] `blocked` removed from `status_values` in schema.yaml; `TERMINAL_STATUSES` and all status-enum consumers updated; `goc validate` rejects `status: blocked` with a message pointing at the migration.
  - [ ] Migration path: every existing card with `status: blocked` is reclassified — dependency-waits (non-terminal `advanced_by`) → `status: open` (derived readiness covers them); exogenous waits → `status: open` + `waiting_on: <reason>`. Provide a `goc` migration command or a documented one-shot; run it on this repo's own deck.
  - [ ] No card in the deck retains `status: blocked` after migration; `goc validate` is clean.
  - [ ] advance-card skill: the `* → blocked` transition is removed; replaced with guidance to set the impediment overlay (`goc wait …`) or rely on derived dependency-readiness.
  - [ ] card-schema skill: status enum + the three-axis model (progress / derived dependency readiness / stored impediment overlay) documented; `STALE_BLOCKED`/`ORPHAN_BLOCKED` references reconciled.
  - [ ] deck skill lifecycle diagram + AGENTS_GOC.md / in-repo AGENTS.md updated; plugin mirrors re-synced.
  - [ ] Breaking-change coordination: landed at/with a release boundary (see project release discipline) since it changes the card-frontmatter contract consumers depend on.
---

# Remove `blocked` from the status enum and migrate existing cards

Child of [blocked-status-conflates-dependency-external-wait-and-deferral](../blocked-status-conflates-dependency-external-wait-and-deferral/)
(see the epic for the full design rationale and literature). Implements
**Decision point 1** and the migration. This is the **breaking** step and lands
**last** — it is `advanced_by` both siblings:

- [derive-dependency-readiness-instead-of-storing-blocked-status](../derive-dependency-readiness-instead-of-storing-blocked-status/)
  must exist so dependency-waits behave correctly once they are flipped to `open`.
- [add-waiting-overlay-with-reason-and-until-date](../add-waiting-overlay-with-reason-and-until-date/)
  must exist so exogenous blocked cards have a destination (`waiting_on`).

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

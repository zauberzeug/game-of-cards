---
title: migrate-existing-blocked-cards-to-open-or-waiting-overlay
summary: |-
  Decomposition of `remove-blocked-from-status-enum-…`: the safe prep
  step. Reclassify this repo's three `status: blocked` cards onto the
  three-axis model BEFORE the enum value is removed — a dependency-wait
  (non-terminal `advanced_by`) becomes `status: open` (derived readiness
  covers it); an exogenous wait becomes `status: open` +
  `waiting_on: <reason>`. No enum/code change here (`blocked` stays a
  valid value), so this is autonomous-pull-safe and unblocks the queue
  while the breaking removal waits for a release boundary.
status: open
stage: null
contribution: medium
created: "2026-05-26T12:11:27Z"
closed_at: null
human_gate: none
advances:
  - remove-blocked-from-status-enum-and-migrate-existing-cards
  - remove-blocked-from-the-status-enum-and-validator
advanced_by: []
tags: [api-contract]
definition_of_done: |
  - [ ] The three current `status: blocked` cards are reclassified:
        - `llms-txt-still-recommends-uv-tool-install-as-preferred`
          (non-terminal `advanced_by`) → `status: open` — derived
          readiness hides it from the queue while its prereq is open.
        - `clarify-agent-unblockable-blocked-cards` (empty
          `advanced_by`, exogenous) → `status: open` +
          `waiting_on: <reason>`.
        - `openclaw-subagent-plugin-tools-alsoallow-ignored` (empty
          `advanced_by`, exogenous; also `human_gate: session`) →
          `status: open` + `waiting_on: <reason>`; gate unchanged.
  - [ ] Each reclassification gets a one-line `log.md` entry recording
        the old `blocked` state and why the new axis (derived vs
        overlay) fits.
  - [ ] No card in the deck retains `status: blocked` after this card.
        `goc validate` is clean (the enum still ACCEPTS `blocked` — this
        card does not change the enum; it just stops using it).
  - [ ] Optional: if a reusable `goc` migration helper is cheap, add it;
        otherwise a documented one-shot is fine — the population is 3
        cards. (Helper is not required to close.)
---

# Migrate existing `blocked` cards off the status axis

Decomposition of the breaking epic
[`remove-blocked-from-status-enum-and-migrate-existing-cards`](../remove-blocked-from-status-enum-and-migrate-existing-cards/)
(see it for the three-axis rationale). This is the **safe prep step**,
extracted so it can drain autonomously: it reclassifies the existing
`blocked` cards while `blocked` is *still a valid enum value*, so it
cannot break `goc validate` and needs no release coordination.

It MUST precede the actual enum removal
([`remove-blocked-from-the-status-enum-and-validator`](../remove-blocked-from-the-status-enum-and-validator/)) —
removing the value while a `blocked` card still exists would break
validation. That ordering is the `advances` edge to that card (it gates
the removal's *closure*).

## The mapping

| current shape | becomes |
|---|---|
| `blocked` + non-terminal `advanced_by` (dependency-wait) | `open` — derived readiness (`card_is_ready`) hides it from the queue until the prereq closes; self-clears |
| `blocked` + empty `advanced_by` (exogenous wait) | `open` + `waiting_on: <reason>` (the shipped impediment overlay) |

The overlay (`waiting_on`/`waiting_until`) already shipped, and derived
readiness already ships — so both destinations exist today. This card
only moves the three existing cards onto them.

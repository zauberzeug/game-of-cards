---
title: schema-enum-surfaces-keep-drifting-into-hardcoded-literals
summary: "Meta-fix umbrella: `schema.yaml` is the documented single source of truth for the card enums, yet the engine repeatedly re-states them as literals far from the schema and each divergence is found and fixed one card at a time. Four instances of the same root-cause shape were the signal to install a structural fix (derive the surfaces from the schema, or guard against re-hardcoding) rather than keep playing whack-a-mole."
status: done
stage: null
contribution: medium
created: "2026-06-03T05:11:57Z"
closed_at: "2026-06-03T05:19:40Z"
human_gate: none
advances: []
advanced_by: []
tags: [meta-fix, api-contract, infra]
definition_of_done: |
  - [x] PROCESS: enumerate every surface in `goc/engine.py` (+ `install.py`) that
        re-states a `schema.yaml` enum as a literal — record the file:line list in
        this card's log.md.
  - [x] MECHANICAL: derive the remaining drift-prone literals from `load_schema()`
        where the value is membership/order that the schema already defines —
        candidates: `STATUS_VALUES` (engine.py:1831), `STAGE_ORDER` (1836),
        `CONTRIBUTION_ORDER`/`CONTRIBUTION_RANK` (1835/1974), and the `--status`
        argparse `choices` in `_build_parser`. Preserve current ordering byte-for-byte.
  - [x] TDD: add a parity guard test that fails if any enum-typed CLI `choices`,
        module-level ordering constant, or renderer column list diverges from the
        corresponding `schema.*` list — so the family stops recurring instance by
        instance.
  - [x] Behavior-preserving for the shipped schema (all existing tests green; no
        output diff for the current six-status / three-contribution / three-gate enums).
  - [x] `uv run goc validate` passes and `uv run python -m unittest discover -s tests` is green.
worker: {who: "claude[bot]", where: main}
---

# Schema enum surfaces keep drifting into hardcoded literals — close the family with a guard

## The pattern

`schema.yaml` is the documented single source of truth for the card
enums (`status_values`, `stage_values`, `contribution_values`,
`human_gate_values`, `waiting_on_values`). Yet the engine repeatedly
re-states those enums as literals far from the schema, and each
divergence is found and fixed one card at a time:

| Closed card | Site it de-hardcoded |
|---|---|
| `goc-new-ignores-schema-human-gate-default-and-contribution-values` | `--gate` default, `--contribution` choices |
| `goc-wait-reason-choices-hardcoded-not-read-from-schema-waiting-on-values` | `--reason` choices vs `waiting_on_values` |
| `triage-render-loop-hardcodes-gate-buckets` | triage render buckets vs `human_gate_values` |
| `board-columns-hardcoded-instead-of-derived-from-schema-status-values` | `render_board` columns vs `status_values` |

That is **four instances of one root-cause shape**. Per the audit-deck
sibling-sweep rule, the 4th instance is the signal to stop playing
whack-a-mole and install a structural fix.

## Remaining known instances (verify + fix)

- `STATUS_VALUES = ("open", "active", "blocked", ...)` — `engine.py:1831`
- `STAGE_ORDER = ["null", "alpha", "beta", "stable"]` — `engine.py:1836`
- `CONTRIBUTION_ORDER = {"high": 0, "medium": 1, "low": 2}` — `engine.py:1835`
- `CONTRIBUTION_RANK = {"high": 9.0, ...}` — `engine.py:1974`
- `--status` argparse `choices=[...]` in `_build_parser`

(The `--contribution` / `--human-gate` choices at `engine.py:2713/2719`
should be audited too — confirm whether they were already migrated by the
`goc-new-...` card or are still literals.)

## Why a guard, not just more fixes

Every individual fix is correct but the family regenerates because nothing
*prevents* the next literal. The in-flight epics
`support-custom-card-workflows-and-statuses` and
`support-custom-frontmatter-fields-with-enum-and-required-when-rules` make
this acute: once a consuming repo can define its own statuses/gates in
`schema.yaml`, every surviving hardcoded literal becomes a silent
correctness bug (the value validates but never renders / is never offered
on the CLI). A parity test that asserts each enum surface derives from
`schema.*` turns the whole class red on the first drift instead of waiting
for a human to notice a dropped card.

## Reachability

All four closed siblings plus the board card had a concrete reachable
input. The remaining literals are the same shape: `load_all_cards()` does
not validate `status` against the schema, and the custom-enum epics
deliberately widen the schema — so any surviving literal that omits a
schema-declared value drops or hides real work with no diagnostic.

## Scope note

This is a meta-fix umbrella, not a monolith. The membership/order
literals above are mechanical to derive; the new parity guard is the
durable deliverable. Keep ordering byte-identical for today's schema so
the change is invisible to current users while closing the drift surface.

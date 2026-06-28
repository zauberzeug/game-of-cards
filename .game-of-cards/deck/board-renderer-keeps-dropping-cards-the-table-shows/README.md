---
title: board-renderer-keeps-dropping-cards-the-table-shows
status: open
stage: null
contribution: medium
created: "2026-06-25T20:33:11Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [meta-fix, api-contract, infra]
summary: "`render_board` re-derives, by hand, which cards from the input set appear on the board — and that derivation has silently dropped cards five separate times (row-limit, superseded, active, worker-filter default, off-enum status), each fixed one card at a time. `render_table` shows every card in its input; the board does not, so the two human-facing renderers disagree about which cards exist. The fix family is structural: guard or share the board's card-inclusion so a card present in the input can no longer be silently excluded."
definition_of_done: |
  - [ ] PROCESS: `## Decision required` resolved — pick the coupling mechanism (shared "bucket these cards" helper reused by both renderers vs. an introspection/parity test that fails the build when the board's rendered card-set is a proper subset of the table's for the same input + filter)
  - [ ] TDD: a regression guard asserts that, for a given card list and filter, every card title `render_table` renders also appears in `render_board` (modulo the board's *documented, intentional* exclusions — e.g. the `queue_only` open-only slice — which must be enumerated explicitly, not left implicit)
  - [ ] MECHANICAL: the chosen shape is implemented so the board can no longer drop a card present in its input without a named, tested reason
  - [ ] PROCESS: link the resolved fix back to the instance cards below (cross-reference or note in their log.md that the family is closed)
  - [ ] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green; `python scripts/sync_plugin_assets.py --check` green
---

# The board renderer keeps dropping cards the table shows

## The pattern

`render_table` (`goc/engine.py:2784`) iterates `for t in cards` and
emits a row for **every** card in its input — the show-everything
contract of the default `goc` queue view. `render_board`
(`goc/engine.py:2992`) instead re-derives, by hand, which cards land on
the board (column bucketing, row caps, filter defaults). That
hand-rolled derivation has silently *dropped* cards present in its
input five separate times, each found and fixed as an individual card:

1. [negative-board-row-limit-hides-cards](../negative-board-row-limit-hides-cards/)
   — a negative `max_rows` sliced every column to empty.
2. [superseded-cards-hidden-from-board](../superseded-cards-hidden-from-board/)
   — superseded cards had no column and vanished.
3. [surface-active-cards-in-board](../surface-active-cards-in-board/)
   — active cards were not surfaced.
4. [board-worker-filter-hides-active-cards-by-applying-open-only-default](../board-worker-filter-hides-active-cards-by-applying-open-only-default/)
   — the worker-scoped board inherited the open-only default and emptied
   the ACTIVE/DONE/… columns.
5. [board-drops-cards-whose-status-is-outside-the-schema-enum](../board-drops-cards-whose-status-is-outside-the-schema-enum/)
   — a card whose status is outside `schema.status_values` was filed
   into no column and discarded.

Five instances of one root-cause shape — "the board excludes a card the
table includes" — is well past the meta-fix threshold (four). Each was
patched at its own site; nothing stops the *next* board change (a new
filter axis, a new column rule, a new renderer) from dropping cards
again.

## Relationship to the marker-coupling card

This is a sibling of
[extend-pull-readiness-coupling-invariant-to-the-board-not-ready-predicate](../extend-pull-readiness-coupling-invariant-to-the-board-not-ready-predicate/),
but a **distinct axis**. That card guards the board's not-ready ⏳
*marker* predicate against drift from `card_is_ready` — i.e. *how a
shown card is annotated*. This card guards *which cards are shown at
all* — set membership, not marker accuracy. The same philosophy
applies (a hand-rolled reimplementation of a contract keeps drifting
from its source of truth), one surface over. Resolving both could share
a design idea but they close on different deliverables.

## Why it matters

The board is the primary human triage surface. When it silently omits a
card the table shows, an operator scanning `goc --board` concludes work
does not exist when it does — and the most dangerous case is the
migration scenario (instance 5): the cards that most need surfacing
(legacy/off-enum status mid-migration) are exactly the ones the board
hides. A structural guard turns the whole family from "find and fix
each leak" into "the build fails if the board drops a card."

## Decision required

Two credible mechanisms; pick one (or a hybrid):

- **(A) Shared card-inclusion helper.** Extract the "given this card
  list + filter, which cards belong in this view" step into one routine
  that both `render_table` and `render_board` consume, so the board
  physically cannot bucket a different set than the table. Board-only
  concerns (column layout, row caps, ⏳ markers) stay in `render_board`;
  only the *membership* decision is shared. Risk: the board's
  intentional `queue_only` open-only slice and per-column row caps must
  be modeled as explicit, named transforms on top of the shared set,
  not folded back into a second hand-rolled filter.

- **(B) Introspection / parity guard test.** Keep the two renderers
  separate but add a coupling test (mirroring
  `tests/test_scheduler_workable_predicate_coupling.py`) that, across a
  `status × human_gate × waiting_on × worker-filter × row-limit`
  cross-product, asserts the set of titles `render_board` renders equals
  the set `render_table` renders minus an *explicitly enumerated* list
  of intentional board exclusions. Any future drift that isn't on the
  allow-list fails the build. Cheaper to land; does not dedupe the
  logic, so the two derivations still exist.

The taste call is whether the intentional divergences (open-only
default, row caps) are clean enough to express as transforms over a
shared set (favoring A) or are better left as separate code with a
guard (favoring B).

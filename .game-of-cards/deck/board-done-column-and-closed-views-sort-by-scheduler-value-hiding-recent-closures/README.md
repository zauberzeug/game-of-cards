---
title: board-done-column-and-closed-views-sort-by-scheduler-value-hiding-recent-closures
summary: "Every closed-card view (the board's DONE, DISPROVED and SUPERSEDED columns, --done, --closed-since) was ordered by sort_default's scheduler key, value then oldest-created, a score the engine itself defines as meaningless for terminal cards. Under the default 20-row cap the board's DONE column froze on the oldest high-value closures, and the newest closure ranked last in every view. Fixed: sort_default lists live cards by the scheduler key, then terminal cards most recently closed first, so every closed-card view leads with recent closures and standup and retrospective no longer re-sort."
status: done
stage: null
contribution: medium
created: "2026-09-28T01:35:52Z"
closed_at: "2026-10-08T05:02:33Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: a reproduce.py builds a deck with more than `--max-rows` older high-contribution closures plus a few recent ones, and asserts the recent closures appear in the board's DONE column and lead `goc --closed-since 7d` — or the run disproves the hypothesis and the card flips to `disproved`
  - [x] TDD: a regression test pins the terminal-status order chosen for the board's terminal columns and the `--done` / `--closed-since` tables (most recent `closed_at` first is the order `standup` and `retrospective` already re-sort into)
  - [x] MECHANICAL: drop the `unverified` tag once reproduce.py lands; the `standup` / `retrospective` Python re-sorts are either kept deliberately or removed
worker: {who: "claude[bot]", where: main}
---

# The board's DONE column and the closed-card views sort by scheduler value, hiding recent closures

## Status

Fixed 2026-10-08. `reproduce.py` confirmed the defect on a scratch deck
(exit 1 on the pre-fix engine) and passes after the fix (exit 0). The
regression test is `tests/test_closed_card_views_sort_by_recency.py`;
all nine of its cases fail on the pre-fix engine.

## Defect (confirmed)

`sort_default` (`goc/engine.py`) ordered every card by the scheduler
key `(-value, -live_direct, created)`, whatever the card's status:
value descending, then live downstream count, then oldest-created first.
Every listing goes through it. `render_board` sorts each status column
with it and then cuts the column to `--max-rows` (default 20).
`_cmd_default` sorts the filtered set with it for the table and the JSON,
so `--done`, `--status <terminal>` and `--closed-since` inherited the
same order.

`value` is a scheduler-axis number. `compute_values` prunes terminal
descendants because completed work can no longer be unblocked, so the
number ranks nothing once a card is closed. Measured in this repo on
2026-10-08, before the fix:

- `goc --status done --json` listed 570 cards. The top row closed on
  2026-05-04, and the newest closure (2026-10-08T04:47:59Z) ranked 570
  of 570.
- `goc --closed-since 7d` put the newest of its 13 closures last.
- `goc --board` opened DONE on `install-command-scaffolds-repo` (closed
  2026-05-04), followed by `… +550 more`.

The scratch deck in `reproduce.py` holds 21 `high` closures from May
plus three closures from the last three days. The three recent cards
carry contributions that run against their recency. On that deck every
view failed: none of the recent three appeared in DONE,
`--closed-since 7d` listed them oldest-first, and `--done --json`
opened on a May closure.

Two skills worked around the order in Python. `standup` re-sorted its
`--closed-since 24h` JSON by `closed_at`, ascending. `retrospective`
re-sorted `--status all` JSON by `closed_at`, descending, before taking
the last N closures. The board had no such escape hatch. Two Context
blocks also read the value order unsorted: `retrospective`'s
(`goc --closed-since 90d --json | head -100`) and `audit-deck`'s
(`goc --done`).

## Fix

`sort_default` now splits its input in two. Live cards (status outside
`TERMINAL_STATUSES`) come first, in the unchanged scheduler order.
Terminal cards follow, most recently closed first, ordered by
`_closed_recency_key`:

- `closed_at` is read through `_closed_at_instant`, so a date-only
  legacy stamp counts as that day's midnight UTC and shares one
  timeline with `...Z` datetimes;
- a missing or unparseable `closed_at` sorts after every dated closure;
- the title breaks ties, so closures that share an instant keep an
  order that does not depend on the input order.

The split lives in `sort_default` rather than at each caller, so every
listing follows one rule, including listings added later. A
single-status set (a board column, `--done`) falls entirely in one
part. `--status all` now lists the queue first and the record after
it, instead of mixing closed cards in among live ones by a value that
is meaningless for them. The pull path (`--ready`, `next-card`,
`pull-card`), the leverage line and the active banner only ever sort
live cards, so their order is unchanged.

Changes to the skills:

- `standup` § 3 and `retrospective` Step 1 drop their Python re-sorts
  and say that the engine supplies the order. `standup`'s list now reads
  newest-first; it used to be oldest-first. The DoD's parenthetical
  says both skills already re-sorted newest-first, but `standup` sorted
  ascending.
- The `deck` skill row "Recently closed cards" is now accurate as
  written. Adding "newest first" to it would push the hot-path skill
  body past its `test_skill_body_size` cap, so the row is unchanged.

## Not in scope

- The table shows a CREATED column but no CLOSED column, so a row does
  not display the closure time it is sorted by. That is a presentation
  choice, not this defect.
- [board-renderer-keeps-dropping-cards-the-table-shows](../board-renderer-keeps-dropping-cards-the-table-shows/)
  (parked on a decision) covers *which* cards the board includes. This
  card changed only their order.

Surfaced by: general-purpose audit hunter (engine query / render
surface), 2026-09-28.

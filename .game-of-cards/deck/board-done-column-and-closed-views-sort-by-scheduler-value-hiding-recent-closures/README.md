---
title: board-done-column-and-closed-views-sort-by-scheduler-value-hiding-recent-closures
summary: "UNVERIFIED. Every closed-card view (the board's DONE, DISPROVED and SUPERSEDED columns, --done, --closed-since) is ordered by sort_default's scheduler key, value then oldest-created, a score the engine itself defines as meaningless for terminal cards. With the default 20-row cap the board's DONE column is frozen on the oldest high-value closures: in this repo the newest closure ranks 556 of 556, so standup and retrospective re-sort by closed_at in Python while the board cannot."
status: active
stage: null
contribution: medium
created: "2026-09-28T01:35:52Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, unverified]
definition_of_done: |
  - [ ] TDD: a reproduce.py builds a deck with more than `--max-rows` older high-contribution closures plus a few recent ones, and asserts the recent closures appear in the board's DONE column and lead `goc --closed-since 7d` — or the run disproves the hypothesis and the card flips to `disproved`
  - [ ] TDD: a regression test pins the terminal-status order chosen for the board's terminal columns and the `--done` / `--closed-since` tables (most recent `closed_at` first is the order `standup` and `retrospective` already re-sort into)
  - [ ] MECHANICAL: drop the `unverified` tag once reproduce.py lands; the `standup` / `retrospective` Python re-sorts are either kept deliberately or removed
worker: {who: "claude[bot]", where: main}
---

# The board's DONE column and the closed-card views sort by scheduler value, hiding recent closures

> **UNVERIFIED.** Surfaced by an audit hunter on the engine query/render
> seam on 2026-09-28. The filing agent re-read the citations and
> re-measured this repo's deck. No `reproduce.py` was written this round;
> the falsification recipe is below.

## Location

All in `goc/engine.py`:

- `:3650-3652`, board columns: every column, terminal ones included, is
  `sort_default(...)`-ed and then cut to `max_rows`:
  `sorted_col = sort_default(by_status[c], values=values, by_title=by_title)`,
  then `by_status[c] = sorted_col[:max_rows]`.
- `:3313-3314`, the `sort_default` key:
  `return (-v, -live_direct(t), t.created)`. That is value descending,
  then live downstream, then oldest-created first ("kanban WIP-aging
  discipline", `:3275`).
- `:4421`, `filtered = sort_default(filtered, ...)`. It applies to every
  table and JSON listing whatever the status filter, so `--done` and
  `--closed-since` inherit the same order.
- `:4038`, `--max-rows ... default=20`.
- `:2950-2955`: "Completed work can no longer be unblocked … Terminal
  edges belong to the record axis instead". In other words, the engine
  itself defines `value` as a scheduler-axis number with no meaning for
  terminal cards.

## Hypothesis

Closed-card views are ordered by a score that measures nothing once a
card is closed. With the default row cap, the board's DONE (and
DISPROVED / SUPERSEDED) column is frozen on the oldest high-contribution
closures. This repo, measured by the filing agent:

- `goc --status done --json` puts the 20 top rows between `2026-05-03`
  and `2026-05-14T04:56:42Z`;
- the newest closure (`2026-09-25T04:55:18Z`) ranks 556 of 556;
- `goc --board` shows `install-command-scaffolds-repo`, closed
  2026-05-04, at the top of DONE, followed by `+536 more`.

The skills contradict the engine order in two ways:

- `deck/SKILL.md:87` sells `goc --closed-since 7d` as "Recently closed
  cards".
- Two skills re-sort the output in Python because the engine order is
  unusable: `standup/SKILL.md:68` sorts by `closed_at`, and
  `retrospective/SKILL.md:51` sorts it in reverse. The board has no such
  escape hatch.

## Why deferred

The citations and the repo measurement are confirmed. No `reproduce.py`
is committed this round. The fix is small, but it touches the shared sort
entry point, and the implementing agent should decide whether terminal
views get their own key there or at each caller.

## Fix direction

Recommended: sort terminal-status rows by `closed_at` descending, with the
title as tie-break, in `render_board`'s terminal columns and in the
table / JSON path whenever the filtered set is terminal-only. The
scheduler key stays for live cards, so `pull-card` / `next-card` are
unaffected.

Related:
[board-renderer-keeps-dropping-cards-the-table-shows](../board-renderer-keeps-dropping-cards-the-table-shows/)
(open) covers *which* cards the board includes, not their order.

## Falsification recipe

Make a scratch deck with 21 high-contribution cards closed in May and
three closed this week. If `goc --board` lists any of the recent three in
DONE, the hypothesis is disproved. It is also disproved if
`goc --closed-since 14d` lists them most-recent-first.

Surfaced by: general-purpose audit hunter (engine query / render
surface), 2026-09-28.

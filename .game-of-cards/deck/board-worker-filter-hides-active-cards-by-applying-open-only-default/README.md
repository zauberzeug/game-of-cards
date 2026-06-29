---
title: board-worker-filter-hides-active-cards-by-applying-open-only-default
summary: "`goc --board --worker X` shows only X's *open* cards — the ACTIVE / DONE / DISPROVED / SUPERSEDED columns are empty. The worker-scoped board path consumes the `filtered` list, which carries the implicit `status: open` default, so every non-open card for that worker vanishes. The board's whole purpose is cross-status flow, and its own active-card banner tells users to `Check goc --board` to find active work — but adding `--worker` then hides exactly that."
status: done
stage: null
contribution: medium
created: "2026-06-25T01:29:02Z"
closed_at: "2026-06-25T01:32:30Z"
human_gate: none
advances:
  - board-renderer-keeps-dropping-cards-the-table-shows
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: regression test asserts that `goc --board --worker X` renders X's `active` (and other non-open) cards, not only X's `open` cards — i.e. the worker-scoped board spans every status column, matching `goc --status all --board --worker X`.
  - [x] MECHANICAL: `engine.py` extends the implicit-status auto-default so a board request (no explicit `--status`/`--done`) resolves `status` to `all`, mirroring the existing `--waiting` / `--closed-since` auto-extend. The contested `board_cards = filtered if (status_filter_explicit or args.worker) else cards` gate line is left untouched (it is owned by `board-view-silently-ignores-filters-other-than-status-and-worker`).
  - [x] TDD: `reproduce.py` exits zero (defect no longer fires).
worker: {who: "claude[bot]", where: main}
---

# `goc --board --worker X` hides active cards by applying the open-only default

## Location

- `goc/engine.py:3442-3450` — the implicit-status default in `_cmd_default`:

  ```python
  elif args.status_flag is None:
      # --waiting and --closed-since both surface cards beyond the open
      # queue (active-impeded cards, closed cards): auto-extend the default
      # status to "all" so the subsequent filter has something to narrow.
      status = (
          "all"
          if (closed_since_threshold is not None or getattr(args, "waiting", False))
          else "open"
      )
  ```

- `goc/engine.py:3485-3486` — the board branch consumes `filtered`
  whenever a worker is named:

  ```python
  if args.board:
      board_cards = filtered if (status_filter_explicit or args.worker) else cards
  ```

## What's broken

When no `--status`/`--done` flag is passed, `status` defaults to
`"open"` (the auto-extend to `"all"` fires only for `--waiting` and
`--closed-since`). `filter_cards(..., status="open", worker=X, ...)`
therefore narrows `filtered` to X's **open** cards.

The board branch then computes `board_cards = filtered` because
`args.worker` is truthy. So `render_board` receives only X's open
cards: the ACTIVE column (the kanban soft-lock / coordination signal
the board exists to surface) and the DONE / DISPROVED / SUPERSEDED
columns are all empty.

`goc --board` with no worker is unaffected — it falls to the `else
cards` branch and renders the full deck across all columns. The
defect is specifically the open-only status default leaking into the
worker-scoped board path.

## Why it matters

The board is the one view designed to span all status columns. The
table renderer's own active-card banner instructs users to
`Check goc --board` to locate active work, but `goc --board --worker X`
— the natural "show me *my* board" invocation — then drops every active
card. A worker checking their own board sees an empty ACTIVE column and
concludes nothing is in progress, when in fact their claimed cards are
simply filtered out. The existing workaround is the unobvious
`goc --status all --board --worker X`.

### Reachability

No exotic input required: any deck where a worker has both open and
non-open cards triggers it. `goc status <title> active` auto-populates
`worker` at claim time, so every claimed card is worker-tagged — the
trigger shape is produced by the normal claim flow, not a hand edit.

## Relationship to `board-view-silently-ignores-filters-other-than-status-and-worker`

That card covers the *opposite* failure on the line below
(`engine.py:3486`): filters **other** than `--status`/`--worker`
(`--tag`, `--ready`, `--contribution`, `--human-gate`, `--waiting`,
`--advances`, `--advanced-by`, `--closed-since`) are *ignored* by the
board, which renders the whole deck. It frames `--worker` as a filter
the board correctly honors. This card is the cost of honoring
`--worker`: it drags the open-only status default with it. The two
fixes touch different lines — that card owns the `board_cards = ...`
gate (3486); this card fixes the status default (3442-3450) — so they
do not collide.

## Empirical evidence

`reproduce.py` builds a temp deck with `worker: alice` cards in `open`
and `active`, then runs the CLI:

- `goc --board --worker alice` → ACTIVE column empty (`alice-active-card`
  absent). **BUG.**
- `goc --board` (no worker) → both cards rendered.
- `goc --status all --board --worker alice` → both cards rendered
  (the workaround).

## Fix (applied)

The board request was added to the implicit-status auto-extend,
alongside `--waiting` / `--closed-since`:

```python
elif args.status_flag is None:
    status = (
        "all"
        if (closed_since_threshold is not None
            or getattr(args, "waiting", False)
            or args.board)
        else "open"
    )
```

For the board path this makes `filtered` span all statuses, so the
worker-scoped board shows every column. The no-worker board path is
unchanged (it still uses `cards`), and the table / JSON paths are never
reached when `--board` is set, so nothing else regresses.

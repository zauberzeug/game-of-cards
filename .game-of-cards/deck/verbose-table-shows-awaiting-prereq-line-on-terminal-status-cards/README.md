---
title: verbose-table-shows-awaiting-prereq-line-on-terminal-status-cards
status: done
stage: null
contribution: medium
created: "2026-06-18T05:24:44Z"
closed_at: "2026-06-18T05:29:57Z"
human_gate: none
summary: "render_table emits the 'awaiting: <prereq> (you may start)' advisory on terminal (done/disproved/superseded) cards, contradicting the board renderer which gates the same dependency signal behind a liveness check. A terminal card cannot start, so the advisory is nonsensical."
advances: []
advanced_by: []
supersedes: []
superseded_by: []
tags: [bug]
definition_of_done: |
  - [x] TDD: a regression test asserts the verbose table omits the `awaiting:` line for a terminal-status card (done/disproved/superseded) carrying a non-terminal `advanced_by` prereq, and still emits it for a live (open/active) card with the same prereq
  - [x] TDD: reproduce.py exits zero (the `awaiting: ... (you may start)` line no longer appears under the terminal card)
  - [x] MECHANICAL: the `awaiting:` emission in `render_table` is gated on `t.status not in TERMINAL_STATUSES`, mirroring the board renderer's `live` gate
worker: {who: "claude[bot]", where: main}
---

# verbose-table-shows-awaiting-prereq-line-on-terminal-status-cards

> Later: the per-renderer liveness gate this card patched is now
> centralized in `engine.dependency_advisory` — see
> [renderers-reimplement-the-dependency-advisory-liveness-gate-and-drift](../renderers-reimplement-the-dependency-advisory-liveness-gate-and-drift/)
> (the meta-fix consolidating board / table / json).

## Location

`goc/engine.py:2677-2679` — the verbose (`-v`) branch of `render_table`.

## What's broken

The verbose table renderer unconditionally computes the dependency-blocker
list and prints the `awaiting:` advisory for **every** card, regardless of
the card's own status:

```python
blockers = dependency_blockers(t, by_title)
if blockers:
    out_lines.append(f"    awaiting: {', '.join(blockers)} (you may start)")
```

`dependency_blockers` (`goc/engine.py:2055`) returns the subset of the
card's `advanced_by` prereqs whose status is non-terminal — it inspects the
*prereqs'* statuses, never the card's own. So a closed card (`done`,
`disproved`, `superseded`) that still carries a non-terminal prereq gets
labelled `awaiting: <prereq> (you may start)`. A terminal card cannot
"start" anything; the suffix is nonsensical on it.

The board renderer already gets this right. `card_cell` gates the identical
dependency signal behind a liveness check at `goc/engine.py:2814`:

```python
live = t.status not in TERMINAL_STATUSES
...
not_ready = live and (
    t.human_gate != "none"
    or (t.status == "open" and dependency_blocked(t, by_title))
    or waiting_impedes(t)
```

So the two renderers disagree about the same card: the board shows a closed
card as plain (not awaiting), while `goc --status all -v` shows it as
`awaiting: ... (you may start)`.

## Empirical evidence

`reproduce.py` builds a two-card deck: `closed-child` (`status: done`,
`advanced_by: [prereq-open]`) and `prereq-open` (`status: open`). Running
`goc --status all -v --no-color`:

```
closed-child  done    -      medium    3.0  none  2026-06-17        1/1
    summary: a closed child with an open prereq
    awaiting: prereq-open (you may start)
prereq-open   open    -      medium    3.0  none  2026-06-18        0/1
    summary: an open prerequisite
```

The `done` card carries `awaiting: prereq-open (you may start)`. Expected:
no `awaiting:` line under a terminal-status card; it should appear only
under live cards.

## Why it matters

The reachability path is ordinary deck shape: any card closed before one of
its `advanced_by` prereqs reaches a terminal status produces this. A child
closed ahead of a still-open parent (or a card disproved/superseded while a
prereq is still open) is exactly such a case — `goc --status all -v` is the
standard cold-read view, so the misleading advisory ships to every reader
who lists closed cards verbosely. The table and the board are meant to
agree on a card's dependency state; this is a single-renderer drift from the
shared `TERMINAL_STATUSES` liveness rule the board already encodes.

## Fix (applied)

`render_table` now gates the blocker computation on liveness, mirroring the
board renderer (`goc/engine.py:2677`):

```python
# Mirror the board renderer's liveness gate (see `card_cell`):
# the dependency advisory is a "you may start" hint, which is
# meaningless on a terminal card. Only live cards show it.
blockers = (
    dependency_blockers(t, by_title)
    if t.status not in TERMINAL_STATUSES
    else []
)
if blockers:
    out_lines.append(f"    awaiting: {', '.join(blockers)} (you may start)")
```

`reproduce.py` now exits 0, and `tests/test_verbose_table_awaiting_liveness.py`
asserts the advisory is omitted for all three terminal statuses while a live
card with the same open prereq keeps it.

---
title: board-truncates-worker-label-to-eight-characters
status: active
stage: null
summary: The kanban board hard-caps the worker label to 8 characters (`claude[bot]` → `@claude[b`), silently hiding coordination info. The cap is a vestige of the old fixed-width board; columns now auto-size, so it serves no layout purpose.
contribution: low
created: "2026-06-07T04:42:29Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] TDD: a regression test renders a board cell for a card whose worker `who` exceeds 8 characters (e.g. `claude[bot]`) and asserts the full identifier appears in the rendered cell — no silent truncation
  - [ ] TDD: reproduce.py exits zero (the full worker label is present in the board output)
  - [ ] MECHANICAL: the `who[:8]` slice at `goc/engine.py` `render_board.card_cell` renders the full `who` instead
  - [ ] PROCESS: full regression suite (`uv run python -m unittest discover -s tests`) stays green
worker: {who: "claude[bot]", where: main}
---

# Board truncates the worker label to eight characters

## Summary

The kanban board (`goc --board`) appends each card's worker as
`@<who>` but hard-caps `who` to its first 8 characters via a `[:8]`
slice. A worker like `claude[bot]` renders as `@claude[b`, silently
mangling the identifier. The cap is a vestige of the old fixed-width
board; columns now auto-size to their widest cell, so the truncation
serves no layout purpose and only hides coordination information.

## Location

`goc/engine.py`, `render_board.card_cell` — the worker-suffix line:

```python
who = _worker_who(t.frontmatter.get("worker"))
if who:
    marker += f" @{who[:8]}"
```

## What's broken

The `who[:8]` slice truncates the worker identifier to 8 characters
with no overflow indicator. `claude[bot]` (11 chars) becomes
`@claude[b`; `github-actions[bot]` becomes `@github-a`. A reader
scanning the board cannot tell which agent or person holds a card.

This directly contradicts two things:

1. **The tool's own stated convention.** `render_board` documents
   (engine.py, just above `col_widths`): *"Surface the row cap rather
   than hiding it: every other capped list in the tool
   (render_active_notice, the tag-sample renderer, the validate
   report) advertises its overflow, so the board does too."* The
   worker label is the one capped value on the board that is hidden
   silently.

2. **The fix already shipped for the title.** The closed card
   [board-active-card-worker-label-not-truncated](../board-active-card-worker-label-not-truncated/)
   switched the board off a fixed 20-char column width specifically so
   the *title* would never be hidden — *"avoiding hidden title
   truncation in the coordination view."* Columns now size to the
   widest rendered cell. That change removed the only reason the
   worker was ever truncated, but left the `[:8]` slice in place. The
   worker `who` is coordination information exactly like the title; it
   should get the same full-render treatment.

## Empirical evidence

```
$ uv run python deck/board-truncates-worker-label-to-eight-characters/reproduce.py
worker frontmatter who: claude[bot]  (11 chars)
ACTIVE column width: 27 chars (room for the full label)
board cell: 'short-title [m] @claude[b'
full '@claude[bot]' present in cell? False
DEFECT: worker label truncated to 8 chars despite the column having room.
```

(Run `reproduce.py` on a clean checkout to regenerate.)

## Why it matters

`goc status <title> active` auto-populates `worker.who` from the git
user name at claim time. In this very repo that value is
`claude[bot]`, `github-actions[bot]`, or a contributor's display name
— routinely longer than 8 characters. So the live board genuinely
shows `@claude[b` / `@github-a` / `@Rodja Tr` today (visible in any
`goc --board` run here). The board is the coordination view that tells
a human or a parallel agent who already holds a card; a mangled worker
label undercuts exactly that purpose, and silently — the reader has no
signal the value was cut.

Reachability: the offending string is produced by `render_board`
itself on every `goc --board` invocation for any active/parked card
whose `worker.who` exceeds 8 characters — no hand-authored input
required.

## Fix

Render the full `who`, dropping the `[:8]` slice, mirroring the
full-title treatment the column auto-sizing already gives the title:

```python
who = _worker_who(t.frontmatter.get("worker"))
if who:
    marker += f" @{who}"
```

The column width is computed from the widest rendered cell after the
markers are appended (see `col_widths`), so the grid stays aligned;
the only effect is that the worker-bearing column grows by however many
characters the full identifier needs — the same contract the title
already enjoys.

---
title: board-and-table-renderers-crash-on-a-card-with-null-status
status: done
stage: null
contribution: medium
created: "2026-06-26T02:06:09Z"
closed_at: "2026-06-26T02:10:28Z"
human_gate: none
advances:
  - bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes
advanced_by: []
tags: [bug, api-contract]
summary: "A single card with `status: null` (or an empty `status:`) parses to a Python `None`, and `Card.status` returns it verbatim. Both `render_table` (the default `goc` view) and `render_board` then call string methods on the value (`_display_width(None)`, `None.upper()`) and crash with a `TypeError`/`AttributeError` — so one malformed card makes the WHOLE deck unlistable, not just the offending row. `goc validate` flags the bad status but you can no longer reach a view to find it."
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (both renderers emit output for a null-status card; defect no longer fires)
  - [x] TDD: a regression test asserts `render_table` and `render_board` both render a card whose `status` parses to `None` without raising
  - [x] MECHANICAL: `Card.status` coerces a `None`/non-string frontmatter value to a string, mirroring the `Card.contribution` property
  - [x] MECHANICAL: behavior-preserving for cards whose status is a normal string (no output diff)
  - [x] PROCESS: `uv run goc validate` passes and `uv run python -m unittest discover -s tests` is green
worker: {who: "claude[bot]", where: main}
---

# Board and table renderers crash on a card with `status: null`

## Location

- `goc/engine.py:735-736` — the `Card.status` property (root cause).
- `goc/engine.py:2822` (`render_table`) and `goc/engine.py:3068`/`3077`
  (`render_board`) — the two crash sites.

## What's broken

The `status` property returns the raw frontmatter value:

```python
@property
def status(self) -> str:
    return self.frontmatter.get("status", "")
```

The `-> str` annotation is a lie. When a card carries `status: null`
(or a bare `status:` with no value), the YAML-lite parser yields a
Python `None` and the key is *present*, so `.get("status", "")`
returns `None` — the `""` default only applies to a missing key.

The sibling `contribution` property already guards against exactly
this shape:

```python
@property
def contribution(self) -> str:
    v = self.frontmatter.get("contribution")
    return "" if v is None else str(v)
```

`status` does not, so `None` (or a non-string like `status: 3`) flows
straight into the renderers. The default table view crashes at
`engine.py:2822`:

```python
max(_display_width(h), max((_display_width(r[i]) for r in rows), default=0))
# _display_width(None) -> TypeError: 'NoneType' object is not iterable
```

and the board crashes at `engine.py:3068`/`3077`, because the
off-enum-status path appends the raw status as a column key and then
upper-cases it:

```python
for t in cards:
    if t.status not in by_status:
        columns.append(t.status)       # appends None
        by_status[t.status] = []
...
_display_width(c.upper())              # None.upper() -> AttributeError
```

The off-enum column path was added by
[board-drops-cards-whose-status-is-outside-the-schema-enum](../board-drops-cards-whose-status-is-outside-the-schema-enum/)
to make the board robust to *any* status string — but it assumed the
status is always a string.

## Empirical evidence

Before the fix, `Card.status` returned `None` and both renderers crashed:

```
parsed Card.status: None
render_table:  CRASH TypeError: 'NoneType' object is not iterable
render_board:  CRASH AttributeError: 'NoneType' object has no attribute 'upper'
```

After coercing in the property, `Card.status` is `""` and both renderers
produce output (reproduce.py exits zero):

```
$ uv run python .game-of-cards/deck/board-and-table-renderers-crash-on-a-card-with-null-status/reproduce.py
parsed Card.status: ''
render_table:  OK
render_board:  OK
```

## Why it matters

A null/empty `status:` is a one-keystroke hand-edit mistake (deleting
a status value, a half-finished card, a bad migration). The reachability
path is direct: a hand-authored or migration-produced card lands in
`.game-of-cards/deck/` with `status:` empty → `load_all_cards()` reads
it → the very next `goc` or `goc --board` invocation crashes for the
*entire deck*. The card that would tell you which entry is broken
(`goc validate` flags `status: None not in [...]`) is reachable, but the
day-to-day read views — the ones an agent or human hits first — are not.
This is strictly worse than the off-enum-status case the board path was
written to handle: there, one card was dropped; here, every card
disappears behind a traceback.

## Fix

Coerce in the `Card.status` property, mirroring `Card.contribution`
(single site, fixes both renderers and any other consumer):

```python
@property
def status(self) -> str:
    v = self.frontmatter.get("status")
    return "" if v is None else str(v)
```

`goc validate` continues to flag the invalid status because it reads
the raw `fm["status"]` value, not the property (`engine.py:1516`). No
engine comparison depends on `Card.status` being `None` (the only
`status is not None` check at `engine.py:2504` is on the filter
argument, not the property), so coercing `None`→`""` is behavior-neutral
for the queue/terminal/ready predicates.

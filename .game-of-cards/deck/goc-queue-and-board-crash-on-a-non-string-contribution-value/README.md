---
title: goc-queue-and-board-crash-on-a-non-string-contribution-value
summary: "`Card.contribution` (`goc/engine.py:649-650`) returned the raw frontmatter value with no string coercion, so a non-string scalar crashed `render_table` and `render_board` with a TypeError. An instance of the broader bare-scalar root cause tracked by `bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes`. Fixed per-consumer here; the load-time shape-validation fix remains the open meta-fix decision."
status: done
stage: null
contribution: medium
created: "2026-06-21T18:57:07Z"
closed_at: "2026-06-21T19:01:11Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — `render_table` (verbose 0 and 1) and `render_board` over a one-card deck whose `contribution` is a non-string scalar (e.g. `42`) both render without raising; a regression test in `tests/test_board.py` covers both renderers plus the None-marker guard.
  - [x] MECHANICAL: `Card.contribution` (`goc/engine.py:649-650`) coerces non-None values to `str` (None/missing stays `""` so the empty-case `[?]` board marker does not regress to `[N]`).
  - [x] MECHANICAL: plugin mirrors synced (`goc/engine.py` is mirrored byte-for-byte into the plugin payloads) and `uv run goc validate` is clean.
worker: {who: "claude[bot]", where: main}
---

# `goc` queue and board crash on a non-string `contribution` value

> Family: an instance of the broader root cause tracked by
> [bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes](../bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes/)
> — the parser accepts any scalar shape on any field and each read-time
> consumer trusts the shape it wants. This card is the non-string-*scalar*
> render-path failure mode (a hard TypeError, vs that card's
> bare-string-on-list char-iteration). Fixed per-consumer here; the
> architectural fix (load-time shape validation across all fields) is the
> open decision on the meta-fix card.

## Location

`goc/engine.py:649-650` — the `Card.contribution` property. The crashes
surface downstream at `goc/engine.py:2688` / `2698` (`render_table`) and
`goc/engine.py:2866` (`render_board`).

## What's broken

`Card.contribution` returns the raw frontmatter value with no string
coercion:

```python
@property
def contribution(self) -> str:
    return self.frontmatter.get("contribution", "")
```

Contrast the `created` property two definitions below, which *does*
coerce and is therefore safe against non-string YAML scalars:

```python
@property
def created(self) -> str:
    v = self.frontmatter.get("created", "")
    return str(v)
```

`load_all_cards()` (`goc/engine.py:772`) loads any card whose
frontmatter parses; it only skips `FrontmatterError`, not schema
violations. So a hand-edited or legacy card with `contribution: 42`
(an int, or any non-string scalar) loads cleanly. The bare `goc`
(`render_table`) and `goc --board` (`render_board`) paths render **all**
loaded cards *before* any validation runs, so one such card takes down
the entire deck view:

- `render_table` builds `rows` with the raw `t.contribution`
  (`engine.py:2685` / `2687`), then computes column widths with
  `len(r[i])` (`engine.py:2688`) and pads with `.ljust(...)`
  (`engine.py:2698`) — `len(42)` raises `TypeError: object of type
  'int' has no len()`.
- `render_board`'s `card_cell` does `c = t.contribution or ""` then
  `c[0]` (`engine.py:2865-2866`) — `42[0]` raises `TypeError: 'int'
  object is not subscriptable`. Note the existing empty/None guard
  (`c[0] if c else '?'`) does **not** save this case: a non-empty int
  is truthy, so it still indexes.

This refutes the closed card
[board-crashes-when-a-card-has-no-contribution-value](../board-crashes-when-a-card-has-no-contribution-value/),
whose summary asserts "the default table renderer survives because it
does not index." That holds only for the empty/`None` shape it fixed;
for a non-string scalar the table renderer crashes on `len()`/`.ljust()`
and the board's empty-case guard still crashes on `c[0]`. Distinct shape,
distinct uncovered crash site.

## Empirical evidence

Before the fix:

```
render_table CRASH: TypeError object of type 'int' has no len()
render_table (verbose) CRASH: TypeError object of type 'int' has no len()
render_board CRASH: TypeError 'int' object is not subscriptable
```

After the fix (reproduce.py exits 0):

```
$ uv run python deck/goc-queue-and-board-crash-on-a-non-string-contribution-value/reproduce.py
compute_values OK (int contribution does not crash the value walk): (0.0, ['self'])
render_table OK (int)
render_table (verbose) OK (int)
render_board OK (int)
render_board OK (None still marked [?])
```

(`compute_values` survives because `CONTRIBUTION_RANK.get(t.contribution, 0.0)`
at `engine.py:2319` uses `.get()` with a default — the int key simply
misses and falls back. The crash is purely in the renderers.)

## Why it matters

Reachability: the frontmatter parser accepts any YAML scalar for
`contribution`, and `load_all_cards()` deliberately tolerates
schema-invalid cards so one bad card never blanks the queue. But the
default `goc` and `goc --board` views render before validating, so a
single legacy or hand-edited card with `contribution: 42` (or any
non-string scalar) takes down the entire deck view for every command
that lists cards — exactly the "one malformed card takes down the whole
board" failure mode the sibling card aimed to eliminate, left open for
the non-string shape.

## Fix

Coerce in the property (close to `created`, but keeping None falsy so
the sibling card's empty-case `[?]` marker does not regress to `[N]`):

```python
@property
def contribution(self) -> str:
    v = self.frontmatter.get("contribution")
    return "" if v is None else str(v)
```

This fixes both renderers (and any other consumer that assumes a
string). `validate` still flags the value as out-of-enum
(`engine.py:1427`), so coercion does not mask the schema violation — it
just keeps the read-only views alive long enough to show it.

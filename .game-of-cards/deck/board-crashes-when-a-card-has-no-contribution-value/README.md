---
title: board-crashes-when-a-card-has-no-contribution-value
summary: "`goc --board` builds each cell's marker with `f\" [{t.contribution[0]}]\"`, indexing the first character of `contribution`. The `--board` path never validates first, so a hand-edited or legacy card that omits `contribution` (property returns `\"\"`) or writes it blank (`contribution:` -> None) loads cleanly and then crashes the renderer with IndexError/TypeError. One malformed card takes down the entire board for the whole deck; the default table renderer survives because it does not index."
status: active
stage: null
contribution: medium
created: "2026-05-27T06:12:13Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — `render_board` over a deck containing a card with blank/absent `contribution` renders without raising.
  - [ ] MECHANICAL: `card_cell` (`goc/engine.py:2210`) tolerates an empty/None `contribution` — emit a placeholder marker (e.g. `[?]`) instead of indexing `[0]`, matching the default table renderer which already survives such a card.
  - [ ] MECHANICAL: plugin mirrors synced (`goc/engine.py` is mirrored byte-for-byte into the plugin payloads); `uv run goc validate` clean.
worker: {who: "claude[bot]", where: main}
---

# `goc --board` crashes on a card with no `contribution` value

## Location

`goc/engine.py:2210`, inside `render_board`'s `card_cell` helper.

## What's broken

The board renderer indexes the first character of `contribution`
unconditionally (`goc/engine.py:2209-2210`):

```python
    def card_cell(t: Card) -> str:
        marker = f" [{t.contribution[0]}]"
```

`contribution` is required *by the schema*, but that requirement is
enforced only by `goc validate` — never by the card loader nor by the
`--board` code path, which renders the raw deck without validating
first. The `contribution` property (`goc/engine.py:489-491`) returns the
empty string when the key is absent:

```python
    @property
    def contribution(self) -> str:
        return self.frontmatter.get("contribution", "")
```

So a card that omits `contribution` yields `""`, and `""[0]` raises
`IndexError`. A card that writes a blank value (`contribution:` in YAML
-> parses to `None`, a present key) yields `None`, and `None[0]` raises
`TypeError`. Either way a single malformed card crashes `card_cell`,
which crashes `render_board`, which crashes `goc --board` for the entire
deck — with an opaque traceback, not a per-card diagnostic.

The default table renderer does **not** index `contribution[0]`, so it
renders the same malformed deck fine. That asymmetry is the tell: two
read commands disagree on whether a missing-`contribution` card is fatal.

## Why it matters

`goc --board` is a primary, advertised read surface. A hand-edited card,
a partially-migrated legacy card, or a card produced by an older/foreign
tool that omits or blanks `contribution` is enough to take the whole
board down for every other card in the deck. Read commands should be
robust to imperfect input and degrade gracefully (the table renderer
already does); crashing on one bad row violates that and gives the user
a stack trace instead of their board.

## Empirical evidence

`uv run python deck/board-crashes-when-a-card-has-no-contribution-value/reproduce.py`:

```
blank (None): render_board CRASHED -> TypeError: 'NoneType' object is not subscriptable

FAIL: one card with no contribution crashes the whole board.
```

A two-card deck (one valid, one with `contribution: None`) crashes
`render_board` with `TypeError` at `card_cell` — the valid card never gets
rendered. The absent-key variant raises `IndexError` the same way. The
script exits 0 once `card_cell` tolerates an empty/None `contribution`.

## Fix

Guard the index in `card_cell` (`goc/engine.py:2210`) so an empty/None
`contribution` degrades to a placeholder rather than crashing, e.g.:

```python
        c = t.contribution or ""
        marker = f" [{c[0] if c else '?'}]"
```

This mirrors the default table renderer's tolerance. Do NOT apply the
fix as part of this filing.

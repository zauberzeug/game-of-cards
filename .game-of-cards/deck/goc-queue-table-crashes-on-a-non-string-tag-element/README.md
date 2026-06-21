---
title: goc-queue-table-crashes-on-a-non-string-tag-element
status: done
stage: null
contribution: medium
created: "2026-06-21T19:03:15Z"
closed_at: "2026-06-21T19:04:48Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — `render_table` (verbose 0 and 1) over a one-card deck whose `tags` list contains a non-string element (e.g. `[bug, 42]`) renders without raising; regression test `test_table_tolerates_non_string_tag_element` in `tests/test_board.py`.
  - [x] MECHANICAL: the tag join in `render_table` (`goc/engine.py:2677`) coerces each element to `str` so a non-string element does not crash the whole view; `validate` still flags the element as a non-canonical tag.
  - [x] MECHANICAL: plugin mirrors synced (`goc/engine.py` is mirrored byte-for-byte into the plugin payloads) and `uv run goc validate` is clean.
worker: {who: "claude[bot]", where: main}
---

# `goc` queue table crashes on a non-string tag element

## Location

`goc/engine.py:2677`, inside `render_table`.

## What's broken

`render_table` joins the first four tags directly:

```python
tags = ",".join(t.tags[:4])
```

The `tags` property (`goc/engine.py:656-659`) only guarantees the value
is a *list*, not that its elements are strings:

```python
@property
def tags(self) -> list[str]:
    v = self.frontmatter.get("tags")
    return v if isinstance(v, list) else []
```

So a card with `tags: [bug, 42]` (a non-string scalar element, e.g.
from a hand edit or a legacy card) loads cleanly — `load_all_cards()`
only skips `FrontmatterError`, not schema violations — and then the
bare `goc` queue view crashes on the join with `TypeError: sequence
item 1: expected str instance, int found`. One malformed card blanks
the entire queue for every command that lists cards.

This is the tag-column sibling of the `contribution`-column crash fixed
in
[goc-queue-and-board-crash-on-a-non-string-contribution-value](../goc-queue-and-board-crash-on-a-non-string-contribution-value/):
same root shape (a non-string frontmatter scalar reaches a renderer
before validation), distinct site. Only `render_table` is affected —
`render_board`'s cell does not render tags, and `render_json` emits the
list as-is (`json.dumps` handles a mixed list).

## Empirical evidence

```
render_table CRASH: TypeError sequence item 1: expected str instance, int found
board OK (no tags in cell)
json OK
```

## Why it matters

Reachability: the frontmatter parser accepts any YAML list for `tags`,
including one with non-string elements, and `load_all_cards()`
deliberately tolerates schema-invalid cards so one bad card never blanks
the queue. But the default `goc` view renders before validating, so a
single legacy or hand-edited card with a non-string tag element takes
down the deck view — the same "one malformed card takes down the whole
board" failure mode being eliminated field-by-field.

## Fix

Coerce each element to `str` at the join site, keeping validation's
canonical-tag check intact (it still flags the element as non-canonical):

```python
tags = ",".join(str(x) for x in t.tags[:4])
```

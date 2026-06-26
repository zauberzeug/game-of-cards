---
title: table-renderer-crashes-on-a-card-with-null-human-gate
status: done
stage: null
contribution: medium
created: "2026-06-26T02:25:06Z"
closed_at: "2026-06-26T02:30:06Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] `Card.human_gate` coerces a present-but-null (or non-string) value to a string, mirroring `Card.status` / `Card.contribution`
  - [x] `render_table` (verbose 0 and 1) no longer crashes on a card whose frontmatter has a bare/null `human_gate:`
  - [x] regression test added asserting all three renderers tolerate a null `human_gate`
  - [x] `reproduce.py` exits non-zero before the fix, zero after
  - [x] `uv run python -m unittest discover -s tests` passes; `uv run goc validate` clean
worker: {who: "claude[bot]", where: main}
---

# table-renderer-crashes-on-a-card-with-null-human-gate

A card whose frontmatter has a bare `human_gate:` key (or `human_gate: null`)
parses to a Python `None` with the key **present**. `Card.human_gate`
(`engine.py:755`) returns `self.frontmatter.get("human_gate", "")` — the `""`
default is never reached because the key exists, so the property returns
`None`. The table renderer then puts `None` into a row cell
(`engine.py:2825` / `2827`) and `_display_width` iterates it, raising
`TypeError: 'NoneType' object is not iterable`. One malformed card makes the
**entire** queue view (`goc`, `goc --status open`, …) unrenderable.

## Why it matters

This is the exact crash class fixed for `status` in commit `eec5c12`
(closing `board-and-table-renderers-crash-on-a-card-with-null-status`),
which coerced both `status` and `contribution` in their properties but left
`human_gate` on the old un-coerced `.get(..., "")` form. The `status`
property's own docstring (`engine.py:737-741`) names this failure mode.
`human_gate` is the last remaining table cell that can be `None`: `stage` is
guarded (`str(...) if not None else "-"`), `created` is `str()`-wrapped, and
`status`/`contribution` are now coerced — so this completes the sibling
sweep rather than opening a new family.

## Reachability path

Any card on disk with a bare or null `human_gate:` field. The YAML-lite
loader (`parse_frontmatter`) parses that to `None` with the key present.
`cli` → `_cmd_default` → `render_table` → `_display_width(None)` crashes.
`render_board` survives (it only does `human_gate != "none"`) and the JSON
dump survives (it serializes `None` directly), matching the read-view
asymmetry the `status` fix addressed.

## Fix

Mirror the `status`/`contribution` properties — coerce `None` to `""` so the
readiness predicate (`card.human_gate != "none"`) keeps treating a malformed
gate as gated/not-ready, exactly as today, while the renderer gets a string.
`goc validate` still flags the invalid raw value (`engine.py:1532-1533`), so
coercion only protects the read view; it does not mask the data error.

```python
@property
def human_gate(self) -> str:
    v = self.frontmatter.get("human_gate")
    return "" if v is None else str(v)
```

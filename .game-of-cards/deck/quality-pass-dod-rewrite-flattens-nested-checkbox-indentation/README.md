---
title: quality-pass-dod-rewrite-flattens-nested-checkbox-indentation
status: done
stage: null
contribution: low
created: "2026-06-21T05:00:35Z"
closed_at: "2026-06-21T05:04:15Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` builds a DoD with a nested `  - [ ]` sub-item, drives `_apply_dod_rewrite` with a verdict targeting that sub-item's box index, and asserts the rewritten line keeps its original two-space indent (`  - [ ] <new text>`), not column 0
  - [x] MECHANICAL: `_apply_dod_rewrite` captures the original line's leading whitespace and re-applies it after the lstrip/prefix reconstruction
  - [x] EMPIRICAL: rerun reproduce.py against the patched engine; output recorded in "Empirical evidence" shows the indent preserved
  - [x] PROCESS: a regression test in `tests/` exercises the indentation-preservation invariant
  - [x] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# `goc quality-pass` DoD rewrite flattens nested checkbox indentation to column 0

## Summary

`_apply_dod_rewrite` (`goc/engine.py:3604`) reconstructs a rewritten DoD
item by `lstrip()`-ing the LLM's `fix` text and writing it back without
restoring the original line's leading whitespace. `_dod_box_indices`
deliberately counts indented (`  - [ ]`) checkboxes, so a verdict that
targets a nested sub-item silently flattens it to column 0 — destroying
the DoD's nesting structure.

## Location

- `goc/engine.py:3604-3621` — `_apply_dod_rewrite`. Specifically the
  `new_text = new_text.lstrip()` at **line 3616** and the assignment
  `lines[line_idx] = new_text` at **line 3619**, which never re-applies
  the original line's indentation.
- `goc/engine.py:548` — `DOD_ANY_BOX = re.compile(r"^[ \t]*- \[[ xX]\]")`
  and `goc/engine.py:604` `_dod_box_indices` count indented checkboxes as
  valid boxes at their own index, so nested items are legitimate rewrite
  targets.

## What's broken

The reconstruction loop discards the original leading whitespace:

```python
for box_idx, line_idx in enumerate(box_indices):
    if box_idx in fix_by_idx:
        new_text = fix_by_idx[box_idx]
        new_text = new_text.lstrip()              # strips the LLM payload's leading ws
        if not new_text.startswith("- ["):
            new_text = f"- [ ] {new_text}"
        lines[line_idx] = new_text                # written at column 0, original indent lost
```

`DOD_ANY_BOX` anchors with `^[ \t]*`, so `_dod_box_indices` returns the
line index of a nested `  - [ ]` sub-item. When a verdict targets that
index, the rewriter rebuilds the line from the bare `fix` text at column
0. A DoD that read

```
- [ ] TDD: top-level criterion
  - [ ] sub-criterion under it
- [x] already-done item
```

comes back with the sub-criterion de-indented to the top level.

## Empirical evidence

Before the fix (`uv run python .game-of-cards/deck/.../reproduce.py`):

```
Rewritten DoD line for the nested sub-item:
'- [ ] sub-criterion reworded to be measurable'

Indentation preserved: False
FAIL: nested sub-item was flattened to column 0
```

After the fix:

```
Rewritten DoD line for the nested sub-item:
'  - [ ] sub-criterion reworded to be measurable'

Indentation preserved: True
PASS: nested sub-item kept its two-space indent
```

## Why it matters

The reachable consumer flow is `goc quality-pass --llm` →
`_apply_verdict_interactive` → user (or `--auto-yes`) accepts a DoD fix →
`_apply_dod_rewrite` rewrites the README. Whenever an accepted fix
targets a nested checkbox, the rewrite silently restructures the DoD:
sub-items that were scoped under a parent become peer top-level items.
A future reader can no longer tell which criteria were sub-tasks of
which, and the change lands with no diff signal beyond the reworded text.

## Relationship to the checkbox-state card

This is a sibling defect to
[goc-quality-pass-dod-rewrite-silently-unchecks-previously-checked-items](../goc-quality-pass-dod-rewrite-silently-unchecks-previously-checked-items/),
which targets the same `_apply_dod_rewrite` lines but a different
attribute: that card is about the hardcoded `- [ ]` prefix flipping
`[x]` → `[ ]` (checkbox **state**), and is `human_gate: decision`
because the fix has a genuine A/B taste call (override the LLM vs.
change the contract). This card is about leading-**indentation** loss,
which has exactly one correct behavior — preserve the original indent —
so it is `human_gate: none`. The fix here leaves the `- [ ]` hardcode
untouched, so the decision card's question remains open and unaffected.

## Fix

Capture the original line's leading whitespace before reconstruction and
re-apply it:

```python
for box_idx, line_idx in enumerate(box_indices):
    if box_idx in fix_by_idx:
        indent = re.match(r"[ \t]*", lines[line_idx]).group(0)
        new_text = fix_by_idx[box_idx].lstrip()
        if not new_text.startswith("- ["):
            new_text = f"- [ ] {new_text}"
        lines[line_idx] = indent + new_text
```

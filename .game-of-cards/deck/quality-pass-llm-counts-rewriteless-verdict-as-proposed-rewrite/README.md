---
title: quality-pass-llm-counts-rewriteless-verdict-as-proposed-rewrite
status: done
stage: null
contribution: medium
created: "2026-06-21T05:20:00Z"
closed_at: "2026-06-21T05:24:46Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
summary: |
  `goc quality-pass --llm`'s `_render_verdict` counts a title/summary verdict
  as a "proposed rewrite" whenever its `ok` is falsy, even when no `rewrite`
  string was supplied — but `_apply_verdict_interactive` only offers/applies a
  rewrite when `rewrite` is truthy. The two sides disagree, so the report
  over-counts ("N with proposed rewrites") and prints a bogus `proposed: ?` line.
definition_of_done: |
  - [x] TDD: reproduce.py exits zero before the fix (defect fires) and the new
        unit test fails before the fix, passes after
  - [x] TDD: `_render_verdict` returns False for a title/summary verdict that is
        `ok: false` but carries no `rewrite` string, and does not print a
        `proposed: ?` line for it
  - [x] TDD: `_render_verdict` still returns True and prints REWRITE when a real
        `rewrite` string is present (no regression), and still flags DoD issues
  - [x] MECHANICAL: the render-side guard mirrors the apply-side guard in
        `_apply_verdict_interactive` (`not ok and rewrite`)
  - [x] PROCESS: reproduce.py inverted to assert the fixed behavior; log.md
        closure entry records the before/after counts
worker: {who: "claude[bot]", where: main}
---

# quality-pass-llm-counts-rewriteless-verdict-as-proposed-rewrite

## Location

`goc/engine.py:3559` — `_render_verdict`. The count is consumed at
`goc/engine.py:3742-3757` (`rewrite_count` → `"N cards audited, N with
proposed rewrites"`).

## What's broken

`_render_verdict` flags a title/summary rewrite based solely on `not ok`,
never checking for a `rewrite` string:

```python
tv = verdict.get("title_verdict") or {}
if tv.get("ok"):
    print("title:   OK")
else:
    has_rewrite = True
    print(f"title:   REWRITE — {tv.get('reason', '?')}")
    print(f"  proposed: {tv.get('rewrite', '?')}")
```

But the apply path, `_apply_verdict_interactive`, guards the actual mutation
with both conditions:

```python
tv = verdict.get("title_verdict") or {}
if not tv.get("ok") and tv.get("rewrite"):
    if ask(f"  apply title rewrite → {tv['rewrite']!r}?"):
        ...
```

(`goc/engine.py:3634-3635` for title, `:3652-3653` for summary). So a verdict
that says `{"ok": false}` with no `rewrite` key — e.g. the LLM flagged a
problem it would not auto-fix, or returned a partial verdict — makes the
render side print `title: REWRITE … proposed: ?` and return `True`,
incrementing `rewrite_count`, while the apply side offers nothing. The final
`"N with proposed rewrites"` over-counts, and the `proposed: ?` line is
meaningless noise.

## Empirical evidence

```
=== _render_verdict ===
has_rewrite (counts toward 'N with proposed rewrites'): True
printed a title REWRITE line:   True
printed a summary REWRITE line: True
printed 'proposed: ?' (no real rewrite): True

=== _apply_verdict_interactive (auto_yes) ===
applied: {'title': False, 'summary': False, 'dod': 0}

BUG: render counts a rewrite the apply path never offers? True
```

## Why it matters

The reachability path: `_run_llm_quality_pass` (`goc/engine.py:3530`) shells
out to the `claude` CLI and parses whatever JSON the model returns into
`verdicts`. A model is free to emit a verdict object with `ok: false` and no
`rewrite` (it judged the title weak but had no confident replacement, or the
response was truncated). `_cmd_quality_pass` feeds each verdict straight to
`_render_verdict` with no shape normalization, so the over-count is reachable
from real model output, not just hand-crafted input. The user then reads "5
with proposed rewrites" but is offered 3, with two `proposed: ?` lines.

## Fix

In `_render_verdict`, gate the title and summary REWRITE branches on a truthy
`rewrite` string, mirroring the apply-side guard. When `ok` is false but no
`rewrite` is present, treat the dimension as having no actionable rewrite
(print OK, or a neutral "flagged, no rewrite offered" line) and do not set
`has_rewrite`. This is the single source of the `rewrite_count` the report
prints, so the count realigns with what `_apply_verdict_interactive` will
actually offer.

This is sibling to
[goc-quality-pass-overstates-dod-rewrite-count-and-drops-unmatched-fixes](../goc-quality-pass-overstates-dod-rewrite-count-and-drops-unmatched-fixes/)
(apply-side DoD over-count) — same "count drifts from what's applied" shape,
different dimension and function. Two instances; not yet a meta-fix family.

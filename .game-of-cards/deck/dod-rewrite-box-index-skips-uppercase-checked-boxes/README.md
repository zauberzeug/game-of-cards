---
title: dod-rewrite-box-index-skips-uppercase-checked-boxes
summary: "`_apply_dod_rewrite` enumerated DoD checkbox lines with `re.match(r\"^\\s*- \\[[ x]\\]\", ln)` (lowercase `x` only), but the canonical box counter `DOD_DONE_BOX` is `re.IGNORECASE` and treats `- [X]` as a checked box. On a card carrying an uppercase `[X]` box, the 0-based index space the LLM verdict targets (`quality-pass --llm`) was misaligned with `box_indices`, so a rewrite could land on the wrong DoD line. Fixed: box indexing routed through `_dod_box_indices`/`DOD_ANY_BOX` (case-insensitive); reproduce.py confirms the misalignment end-to-end."
status: done
stage: null
contribution: medium
created: "2026-05-26T22:25:59Z"
closed_at: "2026-05-26T23:03:45Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] TDD: a `reproduce.py` constructs a card with DoD item 0 = `- [X] ...` (uppercase) and item 1 = `- [ ] ...`, drives `_apply_dod_rewrite` with a verdict targeting `idx: 1`, and shows the edit lands on the wrong physical line (or, post-fix, the right one)
  - [x] TDD: after the fix, `box_indices` and `DOD_DONE_BOX` agree on which lines are boxes for both `[x]` and `[X]`
  - [x] PROCESS: promote out of `unverified` (drop the tag) once the reproduce.py lands; `uv run goc validate` clean
worker: {who: "claude[bot]", where: main}
---

# dod-rewrite-box-index-skips-uppercase-checked-boxes

> **Status: fixed (verified).** Confirmed end-to-end and reconciled.

## The defect

The quality-pass LLM-rewrite path indexed DoD checkbox lines with a
**case-sensitive** regex, while the rest of the engine counts boxes
**case-insensitively**. On a DoD containing an uppercase `[X]` box, the
two disagreed, so the 0-based index the LLM verdict carries no longer
mapped to the physical line the LLM intended — a rewrite could mutate the
wrong DoD item (or silently drop the edit).

`_apply_dod_rewrite` computed:

```python
box_indices = [i for i, ln in enumerate(lines) if re.match(r"^\s*- \[[ x]\]", ln)]
```

The `[ x]` character class matched a space or a lowercase `x` only; an
uppercase `[X]` line was skipped by `box_indices` but counted as a checked
box by the canonical `DOD_DONE_BOX` (`re.IGNORECASE`). `reproduce.py`
confirms: under the old regex, `box_indices` had length 1 for
`"- [X] alpha\n- [ ] beta\n"`, so an `idx: 1` rewrite matched nothing and
the `beta` edit was silently dropped.

## Fix

`goc/engine.py` — added `DOD_ANY_BOX` (matches `- [ ]` / `- [x]` / `- [X]`)
and a `_dod_box_indices(lines)` helper that both `_apply_dod_rewrite` and
the reproduce harness share, so the rewriter's box enumeration agrees with
`DOD_OPEN_BOX + DOD_DONE_BOX` for every case variant.

## Verification

`reproduce.py` exits 0: `box_indices` length matches the canonical count
(2), and an `idx: 1` rewrite lands on `beta` with `[X] alpha` untouched.

Surfaced by a general-purpose audit hunter (engine.py scope) on 2026-05-26.


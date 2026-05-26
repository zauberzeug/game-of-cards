---
title: dod-rewrite-box-index-skips-uppercase-checked-boxes
summary: "UNVERIFIED. `_apply_dod_rewrite` enumerates DoD checkbox lines with `re.match(r\"^\\s*- \\[[ x]\\]\", ln)` (lowercase `x` only), but the canonical box counter `DOD_DONE_BOX` is compiled with `re.IGNORECASE` and treats `- [X]` as a checked box. On a card carrying an uppercase `[X]` box, the 0-based index space the LLM verdict targets (`quality-pass --llm`) is misaligned with `box_indices`, so a rewrite can land on the wrong DoD line. Needs a reproduce.py confirming the misalignment end-to-end."
status: open
stage: null
contribution: medium
created: "2026-05-26T22:25:59Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, unverified]
definition_of_done: |
  - [ ] TDD: a `reproduce.py` constructs a card with DoD item 0 = `- [X] ...` (uppercase) and item 1 = `- [ ] ...`, drives `_apply_dod_rewrite` with a verdict targeting `idx: 1`, and shows the edit lands on the wrong physical line (or, post-fix, the right one)
  - [ ] TDD: after the fix, `box_indices` and `DOD_DONE_BOX` agree on which lines are boxes for both `[x]` and `[X]`
  - [ ] PROCESS: promote out of `unverified` (drop the tag) once the reproduce.py lands; `uv run goc validate` clean
---

# dod-rewrite-box-index-skips-uppercase-checked-boxes

> **Status: unverified.** Static-confirmed citation disagreement; no
> end-to-end `reproduce.py` yet (no budget this audit round).

## Hypothesis

The quality-pass LLM-rewrite path indexes DoD checkbox lines with a
**case-sensitive** regex, while the rest of the engine counts boxes
**case-insensitively**. On a DoD containing an uppercase `[X]` box, the
two disagree, so the 0-based index the LLM verdict carries no longer maps
to the physical line the LLM intended — a rewrite can mutate the wrong DoD
item.

## Location (verbatim)

`goc/engine.py:2649` — `_apply_dod_rewrite`:

```python
box_indices = [i for i, ln in enumerate(lines) if re.match(r"^\s*- \[[ x]\]", ln)]
```

`goc/engine.py:426` — the canonical counter, case-insensitive:

```python
DOD_DONE_BOX = re.compile(r"^[ \t]*- \[x\]", re.MULTILINE | re.IGNORECASE)
```

The `[ x]` character class in the rewriter matches a space or a lowercase
`x` only; an uppercase `[X]` line is skipped by `box_indices` but counted
as a checked box by `DOD_DONE_BOX`.

## Why deferred

Reachable only via `goc quality-pass --llm` and only when a card carries
an uppercase `[X]` box (goc itself emits lowercase, so this needs a
hand-edited or externally-authored card). Real correctness bug, but narrow
trigger — parked for a round with a reproduce.py budget.

## Falsification recipe

- Build a `Card` whose `definition_of_done` is
  `"- [X] alpha\n- [ ] beta\n"`.
- Call `_apply_dod_rewrite(card, [{"idx": 1, "fix": "- [ ] beta REWRITTEN"}])`.
- **Predict (defect):** because the `[X]` line is skipped, `box_indices`
  has length 1 (`beta` at index 0), so `idx: 1` matches nothing OR maps to
  the wrong line — the LLM's "second item" edit misfires.
- **Predict (fixed):** `box_indices` includes both lines; `idx: 1` rewrites
  `beta`.

If the two regexes are reconciled (both `IGNORECASE`, or `box_indices`
reuses `DOD_DONE_BOX`/`DOD_BOX` matching), the disagreement disappears.

Surfaced by a general-purpose audit hunter (engine.py scope) on 2026-05-26.


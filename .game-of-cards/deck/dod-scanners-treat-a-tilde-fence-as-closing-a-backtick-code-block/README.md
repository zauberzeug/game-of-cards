---
title: dod-scanners-treat-a-tilde-fence-as-closing-a-backtick-code-block
status: done
stage: null
contribution: medium
created: "2026-06-05T04:33:35Z"
closed_at: "2026-06-05T04:36:48Z"
human_gate: none
advances:
  - dod-fence-mask-reimplements-commonmark-fences-and-keeps-drifting
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (the `~~~` line inside a backtick block no longer closes it; the real open item is counted)
  - [x] MECHANICAL: `_dod_fenced_mask` tracks the opening fence's character and minimum run length, closing the block only on a same-character fence with a run length >= the opener's (CommonMark §4.5)
  - [x] TDD: a regression test in `tests/` covers a mismatched-fence DoD (backtick block containing a `~~~` line, real open item after)
  - [x] PROCESS: `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# DoD scanners treat a `~~~` fence as closing a backtick code block

## Location

`goc/engine.py:490` — `DOD_FENCE_DELIM = re.compile(r"^[ \t]*(?:`{3,}|~{3,})")`
matches either a backtick run or a tilde run.

`goc/engine.py:493-506` — `_dod_fenced_mask` flips `in_fence` on *any*
line matching `DOD_FENCE_DELIM`, with no memory of which character (or
run length) opened the block.

This mask is the shared substrate for all three DoD scanners:
`count_dod_boxes` (engine.py:619), `_dod_box_indices` (engine.py:509),
and `untagged_dod_items` (engine.py:635) — so the defect propagates to
every reader of the Definition-of-Done.

## What's broken

Per CommonMark §4.5, a fenced code block is closed only by a fence using
the **same character** with a run length **>= the opener's**. A
backtick-opened block that contains a `~~~` line as illustrative text
must keep that `~~~` line *inside* the block. The current mask instead
toggles `in_fence` off on the `~~~`, then back on at the genuine closing
backtick fence — desynchronizing the mask for every line after.

For a DoD whose backtick block illustrates a tilde fence and then carries
a real unchecked item after the closing fence, the mask comes out
`[F, T, F, F, T, T]`: the genuine `- [ ]` at the last line is wrongly
flagged as fenced.

## Why it matters

This is a silent **closure-contract bypass**. With the real open item
masked, `count_dod_boxes` returns `(0, 1)` instead of `(1, 1)`. The card
is not freeform (`done > 0`), so `goc done` (engine.py:3519) and
`_cmd_done_bundle` (engine.py:3595) see zero unchecked boxes and **close
the card despite an unfinished DoD item** — the exact Scrum
Definition-of-Done guarantee the mask was added to protect. The
done-with-unchecked check in `validate_card` (engine.py:1331) inherits
the same undercount, and `_dod_box_indices` returns the wrong index set,
mis-targeting LLM quality-pass verdicts.

## Reachability path

The offending input is authored card text: any card whose
`definition_of_done` block-scalar contains a backtick code block that
illustrates an alternate (`~~~`) fence syntax — exactly the kind of
example a card *about* DoD/markdown parsing naturally carries (the
closed predecessor `dod-checkbox-inside-fenced-code-block-counts-as-real-item-and-blocks-closure`
is one such card). The block-scalar parser loads it verbatim into
`Card.body`, and `count_dod_boxes` scans it on every `goc done`.

## Origin

Adjacent to the closed card
`dod-checkbox-inside-fenced-code-block-counts-as-real-item-and-blocks-closure`,
which introduced `_dod_fenced_mask` to skip fenced checkbox lines but did
not account for fence-character / run-length matching. This is a single
shared function, not a meta-fix family — fixing `_dod_fenced_mask` fixes
all three scanners at once.

## Fix direction

In `_dod_fenced_mask`, when not currently in a fence and a line matches a
fence delimiter, record the opener's character (`` ` `` or `~`) and run
length. While in a fence, close it only when a line is a fence of the
**same character** whose run length is **>= the opener's**; otherwise the
line stays inside the block. Lines that don't satisfy the close
condition remain masked as fenced content.

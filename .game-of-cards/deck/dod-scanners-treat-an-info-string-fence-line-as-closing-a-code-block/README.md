---
title: dod-scanners-treat-an-info-string-fence-line-as-closing-a-code-block
summary: "The shared DoD fenced-code mask treats an info-string fence line (e.g. a backtick-fence carrying a language tag) as a valid closing fence, but per CommonMark section 4.5 a closing fence may not carry an info string. The block closes early and the illustrative `- [ ]` lines that follow are miscounted as real DoD items, making the card impossible to close. Fixed in the closing-fence branch at `goc/engine.py:520`."
status: done
stage: null
contribution: medium
created: "2026-06-05T04:50:01Z"
closed_at: "2026-06-05T04:53:01Z"
human_gate: none
advances:
  - dod-fence-mask-reimplements-commonmark-fences-and-keeps-drifting
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — an `info-string` fence line inside an open block does not close it, and a genuine `- [ ]` after the real closing fence is counted.
  - [x] TDD: regression test asserting `count_dod_boxes` returns the open box for a DoD whose inner fence line carries an info string (e.g. a language tag).
  - [x] MECHANICAL: `_dod_fenced_mask` closing branch requires the post-run remainder to be whitespace-only (CommonMark §4.5), with an explanatory comment.
  - [x] MECHANICAL: existing fence regression tests still pass; opening fences keep their info string allowance.
worker: {who: "claude[bot]", where: main}
---

# DoD fenced-code mask treats an info-string fence line as a valid closing fence

The shared DoD fenced-code mask closes a fenced block on *any* same-character
fence run of length ≥ the opener's — even when the line carries an **info
string** (the language tag commonly written after the opening backticks, e.g.
a ` ```yaml ` line). Per CommonMark §4.5 a closing code fence "may not have an
info string"; such a line is content, not a close. The mask closes the block
early, and the illustrative `- [ ]` lines that follow are miscounted as real
DoD items — making the card impossible to close.

## Location

`goc/engine.py:520-525` — the closing-fence branch of `_dod_fenced_mask`:

```python
if char == fence_char and length >= fence_len:
    # Matching closing fence.
    fence_char = None
    fence_len = 0
    mask.append(True)
    continue
```

The opener regex `DOD_FENCE_DELIM = re.compile(r"^[ \t]*((`{3,})|(~{3,}))")`
captures only the leading fence-character run and ignores any trailing text, so
the closing branch never checks whether the line is "bare". A ` ```yaml ` line
satisfies `char == fence_char and length >= fence_len` and is wrongly accepted
as a close.

## What's broken

CommonMark §4.5: *"The closing code fence … may not have an info string."* An
opening fence may carry an info string (` ```yaml `); a closing fence may be
followed only by spaces or tabs. The current branch enforces the
same-character / run-length rule (added for the tilde-vs-backtick sibling) but
not the no-info-string-on-close rule, so a language-tagged fence line inside an
open block falsely closes it.

## Empirical evidence

```
count_dod_boxes -> open=1 done=1
_dod_box_indices -> [0, 4]
expected open=0 done=1 indices=[0]
```

The ` ```yaml ` line closes the backtick block, so the illustrative
`- [ ] TDD: …` example after it is counted as a real open box.

## Why it matters

This is the exact failure mode the fenced-mask machinery exists to prevent: an
illustrative `- [ ]` inside a fenced block being mistaken for a real DoD item.
The miscount makes `goc done` refuse to close the card (`N unchecked DoD
boxes`) and makes `goc validate` emit a spurious `status=done with N unchecked
boxes` error for any already-closed card whose DoD shows a language-tagged
example block. The offending input is reached by any card author who writes a
fenced example with a language hint in `definition_of_done` — a common and
encouraged markdown habit. It survived the two prior fence fixes
([dod-checkbox-inside-fenced-code-block-counts-as-real-item-and-blocks-closure](../dod-checkbox-inside-fenced-code-block-counts-as-real-item-and-blocks-closure/)
and
[dod-scanners-treat-a-tilde-fence-as-closing-a-backtick-code-block](../dod-scanners-treat-a-tilde-fence-as-closing-a-backtick-code-block/)),
which addressed checkbox masking and fence-character/run-length matching but
not the info-string-on-close rule.

## Fix

In `_dod_fenced_mask`, capture the post-run remainder and treat a same-char
run of length ≥ the opener as a *close* only when that remainder is
whitespace-only. A fence line bearing trailing non-whitespace stays masked as
content. Opening fences are unchanged — they may carry an info string.

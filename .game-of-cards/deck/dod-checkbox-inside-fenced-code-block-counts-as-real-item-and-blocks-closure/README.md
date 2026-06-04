---
title: dod-checkbox-inside-fenced-code-block-counts-as-real-item-and-blocks-closure
summary: "The DoD checkbox scanners (`count_dod_boxes`, `_dod_box_indices`, `untagged_dod_items` in `goc/engine.py`) match `^[ \\t]*- \\[ \\]` line-by-line with no notion of fenced code blocks. A `- [ ]` shown as an example inside a ```-fence within a card's `definition_of_done` is counted as a real unchecked item, so `goc done` (and `goc done --force`) refuses to close the card and the board shows an inflated `N/M` box count."
status: active
stage: null
contribution: medium
created: "2026-06-04T05:31:55Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — a `- [ ]` line inside a fenced code block in `definition_of_done` is not counted as a DoD box (`count_dod_boxes` returns `(0, 1)` for the reproducer's DoD)
  - [ ] TDD: a regression test in `tests/` exercises `count_dod_boxes`, `_dod_box_indices`, and `untagged_dod_items` against a DoD containing a fenced example checkbox and asserts all three agree on the non-fenced line set
  - [ ] MECHANICAL: the three DoD scanners share one fence-tracking helper so they cannot drift apart on fence handling
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` pass
worker: {who: "claude[bot]", where: main}
---

# dod-checkbox-inside-fenced-code-block-counts-as-real-item-and-blocks-closure

## Location

`goc/engine.py:480-484` (the `DOD_OPEN_BOX` / `DOD_DONE_BOX` /
`DOD_ANY_BOX` regexes), `:487-493` (`_dod_box_indices`), `:592-595`
(`count_dod_boxes`), and `:598-610` (`untagged_dod_items`).

## What's broken

All three DoD checkbox scanners match checkbox lines with a flat,
line-anchored regex and no notion of fenced code blocks:

```python
DOD_OPEN_BOX = re.compile(r"^[ \t]*- \[ \]", re.MULTILINE)
DOD_DONE_BOX = re.compile(r"^[ \t]*- \[x\]", re.MULTILINE | re.IGNORECASE)
DOD_ANY_BOX = re.compile(r"^[ \t]*- \[[ xX]\]")

def count_dod_boxes(dod_field: str) -> tuple[int, int]:
    if not isinstance(dod_field, str):
        return 0, 0
    return len(DOD_OPEN_BOX.findall(dod_field)), len(DOD_DONE_BOX.findall(dod_field))
```

`definition_of_done` is a `|` block-scalar frontmatter field
(`engine.py:305` — "`definition_of_done` always uses `|` block
style"), so it can carry arbitrary multi-line markdown, including a
fenced code block that *shows* a checkbox as an example. Every line
matching `^[ \t]*- \[ \]` is counted as a real unchecked box, even
when it sits inside a ```-fence. `load_card` (`engine.py:626-627`)
feeds the whole field to `count_dod_boxes` and stores
`dod_open`/`dod_done`; `_cmd_done` (`engine.py:1293` for validate,
and the `goc done` path) refuses closure whenever `dod_open > 0`.

This is the same root-cause shape as the open sibling
[decide-misparses-fenced-double-hash-line-as-decision-section-terminator](../decide-misparses-fenced-double-hash-line-as-decision-section-terminator/)
(a `## ` line inside a fence terminates the `## Decision required`
match), but a distinct code path (the `definition_of_done`
frontmatter field vs. the card body) and a distinct symptom
(inflated unchecked-box count → unclosable card vs. truncated
deliberation archive). It is the 2nd instance of the shape, not a
meta-fix family yet.

## Empirical evidence

`reproduce.py` output on a clean checkout (pre-fix):

```
count_dod_boxes -> open=1 done=1
untagged_dod_items -> ['- [ ] write a failing test first']
FAIL: expected open=0 done=1; the fenced example line `- [ ] write a failing test first` is being counted as a real unchecked box, so `goc done` refuses to close the card
```

The DoD's one real item (`- [x] MECHANICAL: ...`) is checked, yet
`open=1` because the fenced example `- [ ] write a failing test
first` is miscounted.

## Why it matters

A card that documents anything about DoD formatting — including the
many DoD/checkbox cards already in this deck — naturally shows a
`- [ ]` line as an example inside its own DoD. The moment it does,
the card becomes impossible to close through the normal path:
`goc done` reports `N unchecked DoD boxes; will not mark done`, and
`goc done --force` fails identically because `--force` only bypasses
the *freeform* DoD check, not the unchecked-box count. The board's
`DOD` column also reports an inflated `N/M`. The only escape is to
hand-edit the card to remove the illustrative fence — i.e. to
distort the card's content to satisfy a parser bug. Reachability is
direct: the block-scalar `definition_of_done` field accepts the
offending input verbatim, and any author writing a DoD example
produces it.

## Fix

Add a small shared fence-tracking helper in `engine.py` and route all
three scanners through it so they agree on which lines are "real"
checkbox lines (the existing comments at `engine.py:488-492` and
`:482-484` already require the three to agree):

```python
_DOD_FENCE_DELIM = re.compile(r"^[ \t]*(?:`{3,}|~{3,})")

def _dod_fenced_mask(lines: list[str]) -> list[bool]:
    """Per-line flag: True when the line opens/closes or sits inside a fenced
    code block, and so must not be treated as a DoD checkbox."""
    mask: list[bool] = []
    in_fence = False
    for ln in lines:
        if _DOD_FENCE_DELIM.match(ln):
            in_fence = not in_fence
            mask.append(True)  # the fence delimiter line is never a checkbox
        else:
            mask.append(in_fence)
    return mask
```

`count_dod_boxes`, `_dod_box_indices`, and `untagged_dod_items` then
skip masked lines. This is single-site (all within `engine.py`) and
fence handling lives in exactly one place.

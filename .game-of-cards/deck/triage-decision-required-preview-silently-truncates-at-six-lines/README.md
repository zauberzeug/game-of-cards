---
title: triage-decision-required-preview-silently-truncates-at-six-lines
status: done
stage: null
contribution: medium
created: "2026-06-23T08:33:52Z"
closed_at: "2026-06-23T08:40:15Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
summary: "The text-mode `goc triage` view caps each parked card's `## Decision required` preview at the first 6 lines (`goc/engine.py:5505-5508`) with no `… +N more` continuation marker, so a reader scanning parked decisions sees a section that looks complete but isn't and may record a decision without seeing constraints stated on line 7+."
definition_of_done: |
  - [x] TDD: a regression test feeds a parked card whose `## Decision required` section has more than 6 lines, runs `goc triage`, and asserts an overflow marker (`… +N more`) appears
  - [x] TDD: the same test asserts the marker count matches the number of dropped lines and names `goc show <title>` so the reader can recover the full text
  - [x] MECHANICAL: `_cmd_triage` emits the overflow line only when the preview exceeds 6 lines (no marker on short previews)
  - [x] PROCESS: `uv run python -m unittest discover -s tests` stays green
worker: {who: "claude[bot]", where: main}
---

# triage-decision-required-preview-silently-truncates-at-six-lines

The text-mode `goc triage` view caps each parked card's `## Decision
required` preview at the first 6 lines and emits **nothing** when the
section is longer — no `… +N more`, no continuation marker. A reader
scanning parked decisions sees a section that looks complete but isn't,
and may record a decision via `Skill(decide-card)` without ever seeing
the constraints stated in lines 7+.

## Location

`goc/engine.py:5505-5508`, in `_cmd_triage` (the text-mode renderer):

```python
preview = entry["decision_required"]
if preview:
    for ln in preview.splitlines()[:6]:
        lines.append(f"  > {ln}" if ln else "  >")
```

## What's broken

The `[:6]` slice hard-caps the blockquote preview with no overflow
indicator. This contradicts the overflow-advertising convention the
repo applies everywhere else a list is capped:

- `render_board` at `engine.py:2955`: `f"… +{hidden_by_status[c]} more"`
- the tag-sample renderer at `engine.py:2048`: `f" (+{len(untagged) - 3} more)"`
- `render_active_notice` at `engine.py:3041`: `f", +{len(active) - 3} more"`
- the validate report at `engine.py:3791`: `f"  ... and {len(missing_summary) - 20} more"`

The `render_board` comment block even calls this out explicitly: "every
other capped list in the tool ... advertises its overflow, so the board
does too." The triage preview is the one capped list that still hides it.

The JSON path (`goc triage --json`) emits the full `decision_required`
string (`engine.py:5479`), so the data exists — only the human text view
silently drops the tail.

## Empirical evidence

See `reproduce.py`. On a card whose `## Decision required` section has 8
lines, `goc triage` renders 6 and drops 2 with no marker:

```
total preview lines : 8
rendered (text view): 6
hidden silently     : 2
overflow indicator? : ABSENT
```

## Why it matters

`goc triage` is the human-facing "decisions to make" view that
`Skill(scan-deck)` and `Skill(decide-card)` route a human to. The
`## Decision required` section is precisely where the card author lists
the options and constraints the human must weigh, and such sections
routinely exceed 6 lines (option lists plus trade-off bullets plus
framing prose). Any ordinary multi-line decision section reaches this
branch — no malformed input needed. The reader is shown a
confidently-formatted but silently-incomplete briefing at the exact
moment they make an irreversible call.

## Fix

After the 6-line loop, append an overflow line when more lines exist,
matching the repo-wide `… +N more` idiom and pointing at `goc show` for
recovery:

```python
preview_lines = preview.splitlines()
for ln in preview_lines[:6]:
    lines.append(f"  > {ln}" if ln else "  >")
if len(preview_lines) > 6:
    lines.append(
        f"  > … +{len(preview_lines) - 6} more lines "
        f"(see `goc show {entry['title']}`)"
    )
```

Single-site, mechanical, no design decision — the overflow-advertising
convention is already established repo-wide.

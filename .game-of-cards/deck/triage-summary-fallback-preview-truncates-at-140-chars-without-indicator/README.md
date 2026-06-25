---
title: triage-summary-fallback-preview-truncates-at-140-chars-without-indicator
status: active
stage: null
contribution: medium
created: "2026-06-25T01:52:22Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
summary: "`goc triage`'s summary-fallback preview hard-cuts a card's summary at 140 characters with a bare `[:140]` slice and prints the fragment raw — no `…`, no `(see goc show …)` pointer. A long summary masquerades as complete and is clipped mid-word. The sibling `decision_required` branch already advertises its clip; this branch silently does not."
definition_of_done: |
  - [ ] `reproduce.py` exits non-zero against the current engine (defect present) and zero after the fix.
  - [ ] The summary-fallback branch in `_cmd_triage` advertises the clip when the preview is shortened (append `…` and a `(see goc show <title>)` pointer), matching the `decision_required` branch convention.
  - [ ] Short summaries (≤140 chars, single line) are printed unchanged — no spurious indicator.
  - [ ] A regression test in `tests/` asserts a clipped summary preview carries an indicator and a short one does not.
  - [ ] `uv run python -m unittest discover -s tests` passes; `uv run goc validate` passes.
worker: {who: "claude[bot]", where: main}
---

# `goc triage` summary fallback truncates at 140 chars without an indicator

## Problem

`_cmd_triage` (`goc/engine.py:5601-5603`) renders a parked card's preview from
its `summary` when the card has **no** `## Decision required` body section:

```python
elif entry["summary"]:
    first = entry["summary"].splitlines()[0][:140]
    lines.append(f"  > {first}")
```

The `[:140]` slice hard-cuts the text and prints the fragment raw — no `…`, no
"more", no pointer. A summary longer than 140 chars is emitted as a mid-word
fragment that looks like the whole summary.

This is inconsistent with the sibling `decision_required` branch seven lines
above (`engine.py:5592-5600`), which advertises its clip:

```python
if len(preview_lines) > 6:
    lines.append(
        f"  > … +{len(preview_lines) - 6} more lines "
        f"(see `goc show {entry['title']}`)"
    )
```

and with every other capped list in the tool (`render_board`'s `… +N more`,
the missing-summary list's `... and N more`).

## Reachability

`goc triage` with no flags, on any deck containing an open card with
`human_gate ∈ {decision, session}` that has a `summary` but no
`## Decision required` section. This is the normal shape: `goc new` always
scaffolds a `summary` but does not require the decision-required section, so the
fallback branch is the common path for parked cards. The JSON path
(`goc triage --json`) is unaffected — it emits the full untruncated summary
(`engine.py:5566`).

## Evidence

`reproduce.py` builds an isolated deck with one parked card whose summary is
283 chars and which has no `## Decision required` section, then runs
`_cmd_triage`. Current output:

```
summary length          : 283 chars
preview body length     : 140 chars
preview line            : '  > This card needs a human decision … the tradeoffs around laten'
shows full summary?     : False
advertises the clip?    : False
DEFECT: preview is silently truncated mid-text with no indicator.
```

The preview is cut mid-word at "laten" with nothing signalling the clip.

## Fix

In the summary-fallback branch, advertise the clip when the preview is shortened
(first line truncated at 140 chars, or extra lines dropped), following the
`decision_required` branch convention: append ` …` and a
`(see goc show <title>)` pointer. Leave short single-line summaries unchanged.

## Not a duplicate

Closest existing card is `triage-decision-required-preview-silently-truncates-at-six-lines`
(**done**) — that fixed the *other* branch (the `decision_required` preview) and
a *different* mechanism (a 6-**line** cap). The `elif entry["summary"]` fallback
and its 140-**character** cut were never touched.

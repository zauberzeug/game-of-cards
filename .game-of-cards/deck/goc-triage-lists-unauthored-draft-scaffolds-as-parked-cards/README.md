---
title: goc-triage-lists-unauthored-draft-scaffolds-as-parked-cards
status: active
stage: null
contribution: medium
created: "2026-06-30T01:31:35Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: a regression test asserts `goc triage` (and `--json`) omits an `open` + `human_gate != none` card carrying `draft: true`
  - [ ] The `_cmd_triage` candidate filter excludes drafts via the shared `card_is_draft` predicate (not a re-hand-rolled flag read)
  - [ ] reproduce.py exits zero (draft no longer leaks into either triage path)
  - [ ] `uv run python -m unittest discover -s tests` passes
  - [ ] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# `goc triage` lists unauthored draft scaffolds as parked cards

## Location

`goc/engine.py:5965` — `_cmd_triage`.

## What's broken

Every canonical listing surface hides draft scaffolds (`draft: true`)
through the shared `card_is_draft` predicate. `filter_cards` — the path
behind the default queue, `--status`, `--board`, and `render_json` —
applies it explicitly (`goc/engine.py:2612-2613`):

```python
# Unauthored scaffolds (draft flag or surviving placeholder) are hidden from
# every listing except `--status all`: a draft is not yet real work and must
# not appear as queueable.
if status != "all":
    out = [t for t in out if not card_is_draft(t)]
```

But `_cmd_triage` builds its own candidate set with a hand-rolled
filter that never consults `card_is_draft`:

```python
all_cards = [t for t in load_all_cards() if t.status == "open" and t.human_gate != "none"]
```

So a freshly scaffolded card — `goc new` always stamps `draft: true`
and lets the filer choose a gate — that is filed with `--gate decision`
or `--gate session` is surfaced by `goc triage` (and `goc triage
--json`) as a card "Waiting on you," even though the same card is
correctly invisible to `goc`, `goc --status open`, and the board.

## Empirical evidence

`reproduce.py` constructs the exact card shape `goc new
<title> --gate decision` produces (an `open`, `human_gate: decision`,
`draft: true` card) and runs both filters:

```
card_is_draft: True | status: open | gate: decision
filter_cards (queue/board/json) shows: []
triage filter (engine.py:5965) shows: ['draft-card-needs-a-decision']
```

The draft is hidden by the canonical path and leaked by triage.

## Why it matters

The draft flag exists precisely to signal "this is not real work yet —
do not act on it." `goc triage` is the canonical "Waiting on you (gate
≠ none)" view a human scans to decide what to unblock. Surfacing an
unauthored scaffold there presents a human with a pending *decision*
about a card that has no authored scope to decide on — the exact
false signal the draft state was added to suppress (see the draft
contract introduced by `placeholder-cards-superseded-before-they-are-authored`).

Reachability: `goc new` stamps `draft: true` on every scaffold and
accepts `--gate decision` / `--gate session` at filing time, so an
open + gated + draft card is a routine intermediate state — the window
between `goc new ... --gate decision` and the filer authoring/claiming
the card. Any `goc triage` run in that window leaks it.

This is the draft-direction sibling of
[parked-active-cards-are-missing-from-goc-triage](../parked-active-cards-are-missing-from-goc-triage/),
which catalogues the *opposite* divergence of the same hand-rolled
triage filter: it drops `active` cards that raised their gate
mid-session. Both stem from `_cmd_triage` re-implementing the
candidate filter instead of routing through `filter_cards`.

## Fix

Add the shared draft exclusion to the `_cmd_triage` comprehension:

```python
all_cards = [
    t for t in load_all_cards()
    if t.status == "open" and t.human_gate != "none" and not card_is_draft(t)
]
```

This uses the single not-yet-real predicate rather than re-reading the
flag, matching `filter_cards` and `card_is_ready`.

---
title: ready-flag-help-text-overstates-advanced-by-prereq-filtering
summary: "The `goc --ready` CLI help text claims the filter excludes cards with 'no non-terminal advanced_by prereqs', but the predicate it actually calls (`card_is_ready`) was deliberately changed to ignore `advanced_by` entirely. The help is stale documentation left behind when `make-advances-gate-closure-not-the-pull-queue` reversed the semantics — a reader trusting `--help` expects prereq-blocked cards hidden; they are not."
status: open
stage: null
contribution: medium
created: "2026-05-27T06:10:26Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, documentation]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero (the `--ready` help string no longer claims advanced_by prereq filtering, and the claim matches `card_is_ready`'s actual behaviour).
  - [ ] MECHANICAL: the `--ready` argparse help at `goc/engine.py:2319-2321` is rewritten to describe the real predicate (status open, human_gate none, no active waiting_on impediment) — `advanced_by` prereqs are advisory only and do NOT gate readiness.
  - [ ] MECHANICAL: plugin mirrors synced if any (this string lives only in `goc/engine.py`, which is mirrored byte-for-byte into the plugin payloads); `uv run goc validate` clean.
---

# `--ready` help text overstates advanced_by prereq filtering

## Location

`goc/engine.py:2319-2321` (the `--ready` argparse help string) contradicts
`goc/engine.py:1683-1696` (the `card_is_ready` predicate it wires to).

## What's broken

The `--ready` flag advertises a filter behaviour the code no longer implements.

The argparse help (`goc/engine.py:2319-2321`):

```python
parser.add_argument("--ready", action="store_true",
                    help="Filter to ready-to-pull cards (status open, human_gate none, "
                    "no non-terminal advanced_by prereqs). Defaults --status to open.")
```

But the predicate `--ready` actually calls, `card_is_ready`, was deliberately
changed to NOT inspect `advanced_by` at all (`goc/engine.py:1683-1696`):

```python
    Non-terminal `advanced_by` prereqs do NOT block readiness — an
    `advances` edge is a "should be done first" (value-flow + closure
    gate + soft priority bias), not a "must wait to start". The hard
    "must wait to start" signal is the explicit impediment overlay
    (`waiting_on` / `waiting_until`). ...
    """
    if card.status != "open":
        return False
    if card.human_gate != "none":
        return False
    if waiting_impedes(card):
        return False
    return True
```

The help string claims `--ready` excludes cards with non-terminal
`advanced_by` prereqs; the predicate does no such check. The clause
`"no non-terminal advanced_by prereqs"` is stale — it describes the
predicate's behaviour *before* [make-advances-gate-closure-not-the-pull-queue](../make-advances-gate-closure-not-the-pull-queue/)
(done) reversed the semantics. That card's closure log enumerates the
surfaces it updated (the predicate, the `-v` label, the board marker,
JSON keys, four skill bodies) but the `--ready` argparse help string was
missed.

## Why it matters

`--help` output is a public CLI contract surface, and `--ready` is the
exact filter the autonomous `pull-card` / `next-card` loops describe as
their queue. A reader (human or agent) trusting the help expects
prereq-blocked cards to be hidden from `--ready`; they are not. The
help asserts a contract the engine intentionally abandoned hours after
the rest of the surfaces were corrected — precisely the doc-drift the
deck's read-pattern guarantee is meant to prevent. It is live on this
repo's own deck: `blocked-status-conflates-dependency-external-wait-and-deferral`
is open, `human_gate: none`, has a non-terminal `advanced_by` prereq,
yet appears under `goc --ready` — contradicting the help's promise.

## Empirical evidence

`uv run python deck/ready-flag-help-text-overstates-advanced-by-prereq-filtering/reproduce.py`:

```
--ready help string: 'Filter to ready-to-pull cards (status open, human_gate none, no non-terminal advanced_by prereqs). Defaults --status to open.'
  mentions 'advanced_by prereq(s)': True
card_is_ready(dependent with open advanced_by prereq) = True
  (help text implies this should be False / filtered out)

FAIL: --ready help promises advanced_by-prereq filtering that card_is_ready does not perform (doc/code drift).
```

The script reads the real `--ready` help via `engine._build_parser()`
and shows a card the help would exclude (open, gate none, non-terminal
`advanced_by` prereq) is in fact reported ready by `card_is_ready`. It
exits 0 once the help string is corrected.

## Fix

Rewrite the `--ready` help string (`goc/engine.py:2319-2321`) to match
`card_is_ready`, e.g.:

```python
parser.add_argument("--ready", action="store_true",
                    help="Filter to ready-to-pull cards (status open, human_gate none, "
                    "no active waiting_on impediment). Defaults --status to open.")
```

`advanced_by` prereqs are advisory (closure gate + soft priority), not a
start-gate, so they must not be named as a `--ready` filter criterion.
Do NOT apply the fix as part of this filing.

---
title: goc-waiting-default-status-hides-active-impeded-cards
summary: "`goc --waiting` defaults its status filter to `open`, so an `active` card carrying an impediment overlay is dropped before the `--waiting` filter runs — invisible in the very view meant to surface impeded work. `--closed-since` already auto-extends the default status to `all`; `--waiting` should do the same."
status: done
stage: null
contribution: low
created: "2026-06-21T12:19:06Z"
closed_at: "2026-06-21T12:23:31Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (an `active` + `waiting_on` card appears in `goc --waiting` output)
  - [x] TDD: a regression test asserts `goc --waiting` (no explicit `--status`) surfaces both an `open` and an `active` impeded card, and that explicit `--status open` still narrows to open
  - [x] MECHANICAL: `_cmd_default` extends the default status to `all` when `--waiting` is set and `--status` is not explicit, mirroring the `--closed-since` precedent
  - [x] uv run goc validate passes
worker: {who: "claude[bot]", where: main}
---

# `goc --waiting` default status hides active impeded cards

## Location

`goc/engine.py:3346-3347` (the default-status branch in `_cmd_default`) and
`goc/engine.py:3378-3379` (the `--waiting` post-filter).

## What's broken

The `--waiting` flag is the operator's impediment view —
`engine.py:3061` documents it as:

> Filter to cards carrying a waiting_on overlay.

The three-axis stuck model (AGENTS.md; `waiting_impedes` docstring at
`engine.py:2182`) states the impediment overlay is orthogonal to progress
status: **a card may be `status: active` AND carry `waiting_on`.** So the
impediment view must include active impeded cards.

But `_cmd_default` resolves the default status filter like this:

```python
elif args.status_flag is None:
    status = "all" if closed_since_threshold is not None else "open"
```

`--closed-since` auto-extends the default to `"all"`; **`--waiting` has no
equivalent clause.** The `--waiting` filter then runs *after*
`filter_cards(..., status="open", ...)`:

```python
if getattr(args, "waiting", False):
    filtered = [t for t in filtered if t.waiting_on is not None]
```

Any non-`open` card — including an `active` impeded card — is already
dropped by the status filter before `--waiting` ever sees it.

This is independent of the two already-filed `--waiting` predicate bugs
([waiting-flag-filters-on-waiting-on-field-not-the-impediment-overlay](../waiting-flag-filters-on-waiting-on-field-not-the-impediment-overlay/),
[goc-waiting-filter-drifts-from-engine-on-elapsed-and-bare-waits](../goc-waiting-filter-drifts-from-engine-on-elapsed-and-bare-waits/)),
which both target the `waiting_on is not None` vs `waiting_impedes`
predicate (the `waiting_on` × `waiting_until` matrix). Even with their fix
applied, the `status="open"` filter removes the active card before the
`--waiting` filter runs, so this defect persists.

## Empirical evidence

Two impeded cards in an isolated deck — one `open`, one `active` — both
carrying `waiting_on: external`. `reproduce.py` reads `goc --waiting
--json` (the human-facing ACTIVE notice itself names the active card, so a
table-substring check would pass spuriously):

```
--- goc --waiting (default status), titles ---
['open-impeded']
open-impeded surfaced:   True
active-impeded surfaced: False

FAIL: active impeded card is hidden from `goc --waiting` because the
default status filter is `open`.
```

The default-status `--waiting` view omits `active-impeded`. Only
`--status all` (or the fix below) surfaces it.

## Why it matters

`goc --waiting` is where an operator (and the standup skill, which lists
"active and impeded cards") goes to find impeded work. An `active` card
parked on an external dependency is exactly that work, yet it is invisible
in the default view. The reachability path is direct: any
`goc wait <active-card> --reason external` produces an `active` card with
`waiting_on` set, which `_cmd_default` then hides from `goc --waiting`.

## Fix (applied)

`_cmd_default` now mirrors the `--closed-since` precedent one line up —
the default status extends to `all` when `--waiting` is set and `--status`
is not explicit:

```python
elif args.status_flag is None:
    # --waiting and --closed-since both surface cards beyond the open
    # queue (active-impeded cards, closed cards): auto-extend the default
    # status to "all" so the subsequent filter has something to narrow.
    status = (
        "all"
        if (closed_since_threshold is not None or getattr(args, "waiting", False))
        else "open"
    )
```

The `--waiting` filter at `engine.py:3378-3379` then does the real
narrowing by overlay presence, regardless of progress status. An explicit
`--status open` (or any explicit status) still takes the `else` branch and
narrows as before, so `goc --waiting --status open` keeps working.

This is single-site and gate-free: the correct behavior is determined by
the in-function precedent (`--closed-since` → `all`) and the documented
three-axis model; there is no choice between alternatives to make.

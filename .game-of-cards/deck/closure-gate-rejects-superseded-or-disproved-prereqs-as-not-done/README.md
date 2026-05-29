---
title: closure-gate-rejects-superseded-or-disproved-prereqs-as-not-done
summary: "The `advanced-by-closed` closure gate (engine.py:3399) counts an upstream `advanced_by` prereq as unmet unless its status is exactly `done`, but every other predicate over the same edge — `dependency_blockers` (engine.py:1662) and the `compute_values` scheduler prune — treats `{done, disproved, superseded}` (TERMINAL_STATUSES) as resolved. A card whose prereq was superseded or disproved therefore shows 'awaiting: nothing' everywhere yet `goc done`/`attest` blocks its closure with '1 not done', nudging the user toward a record-destroying `goc unadvance`."
status: done
stage: null
contribution: high
created: "2026-05-27T05:59:14Z"
closed_at: "2026-05-27T06:03:25Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (closure gate accepts a superseded or disproved upstream prereq, matching `dependency_blockers`).
  - [x] MECHANICAL: the `advanced-by-closed` check in `_run_derived_check` (engine.py ~3399) uses `not in TERMINAL_STATUSES` instead of `!= "done"`, so the three predicates over the `advanced_by` edge agree.
  - [x] TDD: a regression test asserts the gate passes for `superseded`/`disproved` upstreams and still fails for `open`/`active` upstreams.
  - [x] MECHANICAL: `uv run goc validate` clean; plugin-asset sync `--check` green (no doc surface claims `done`-only closure; if any does, reconcile it).
worker: {who: "claude[bot]", where: main}
---

# Closure gate rejects superseded/disproved prereqs as "not done"

## Location

- `goc/engine.py:3399` — the `advanced-by-closed` derived closure check.
- `goc/engine.py:1662` — `dependency_blockers`, the advisory predicate.
- `goc/engine.py:1646` — `TERMINAL_STATUSES = frozenset({"done", "disproved", "superseded"})`.

## What's broken

Three predicates read the same `advanced_by` edge but disagree on what
counts as a *resolved* upstream.

The advisory predicate (`dependency_blockers`, drives the `-v` "awaiting"
line, the `--board` marker, and `--json`) treats any **terminal** status
as resolved:

```python
# engine.py:1662
if upstream is None or upstream.status not in TERMINAL_STATUSES:
    blockers.append(prereq)
```

The `compute_values` scheduler prune (engine.py:1838) likewise skips
`dest_card.status in TERMINAL_STATUSES`. But the **closure gate**, run by
`goc done` / `goc attest`, accepts only the literal `done`:

```python
# engine.py:3399  (inside _run_derived_check, name == "advanced-by-closed")
unclosed = [t for t in advanced_by if t in by_title and by_title[t].status != "done"]
if unclosed:
    ...
    return False, f"{len(unclosed)} not done: {sample} — {hint}"
```

So if an upstream prereq was legitimately **superseded** (its work
absorbed by a successor) or **disproved** (the prereq turned out moot),
the downstream card shows `awaiting: nothing` in every display, yet
attestation refuses to close it with `1 not done: X`. Worse, the hint
recommends `goc unadvance` — which would delete a true *record-axis*
edge the deck is supposed to preserve (per AGENTS.md "The deck is both a
scheduler and a record").

This contradicts the resolved set the rest of the engine already agreed
on: `TERMINAL_STATUSES` is the project's single definition of "no longer
in play", and `done` is only one of its three members.

## Empirical evidence

`uv run python .game-of-cards/deck/closure-gate-rejects-superseded-or-disproved-prereqs-as-not-done/reproduce.py`
(invokes the real `engine._run_derived_check`):

```
TERMINAL_STATUSES = ['disproved', 'done', 'superseded']

upstream X status = 'superseded'
  dependency_blockers(Y) = []  (empty => display says 'awaiting: nothing')
  closure gate(Y)        = False  (1 not done: X-upstream — ... `goc unadvance` ...)
  >>> INCONSISTENT: display says resolved, closure gate blocks

upstream X status = 'disproved'
  dependency_blockers(Y) = []  (empty => display says 'awaiting: nothing')
  closure gate(Y)        = False  (1 not done: X-upstream — ...)
  >>> INCONSISTENT: display says resolved, closure gate blocks

upstream X status = 'done'
  closure gate(Y)        = True  (all 1 done)
  consistent

DEFECT CONFIRMED: 2 terminal status(es) treated as resolved by dependency_blockers
but rejected by the closure gate.
```

## Why it matters

Supersession is a first-class, documented transition
(`goc status <old> superseded --by <new>`), and the deck deliberately
keeps closed-card relationship edges for the record axis. A card that
depended on work which was then re-routed through a successor is exactly
the case where the downstream is now free to close — but the gate jams
it and points at the one command (`unadvance`) that erases the history
the record axis exists to keep. The inconsistency is silent: nothing in
the queue display warns the author their card is unclosable until they
try to attest.

## Fix

In `_run_derived_check`'s `advanced-by-closed` branch (engine.py:3399),
replace the `done`-only test with the shared resolved-set predicate:

```python
unclosed = [
    t for t in advanced_by
    if t in by_title and by_title[t].status not in TERMINAL_STATUSES
]
```

This makes the closure gate agree with `dependency_blockers` and the
scheduler prune. Add a regression test covering all four upstream
statuses (`done`/`superseded`/`disproved` pass; `open`/`active` fail).
Check the success message ("all N done") and any doc surface for
`done`-specific wording and soften to "closed/terminal" if needed.

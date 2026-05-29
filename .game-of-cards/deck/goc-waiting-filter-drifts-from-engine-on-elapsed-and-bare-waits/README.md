---
title: goc-waiting-filter-drifts-from-engine-on-elapsed-and-bare-waits
summary: "`goc --waiting` filters with `t.waiting_on is not None` (engine.py:2846), but the engine's authoritative `waiting_impedes` predicate (engine.py:1752) walks a four-cell matrix over both `waiting_on` AND `waiting_until`. The CLI flag disagrees with the engine in two cells: it INCLUDES cards whose `waiting_until` has elapsed (engine has already resurfaced them) and it OMITS bare deferrals where only `waiting_until` is set. Same drift class as the recent session-start `_is_impeded` precision fix and the just-filed `standup-impeded-filter-drifts-from-engine-on-elapsed-and-bare-waits` — except this time the engine's own CLI lies about its own impedance predicate."
status: open
stage: null
contribution: medium
created: "2026-05-29T11:35:23Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, documentation]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — `goc --waiting` output matches `{t.title for t in cards if waiting_impedes(t)}` across the four-cell `waiting_on` x `waiting_until` matrix.
  - [ ] TDD: a unittest under `tests/` exercises the same matrix against the CLI flag so a future refactor cannot reintroduce the drift silently.
  - [ ] EMPIRICAL: the chosen interpretation (see "## Decision required") is recorded in `log.md` with the principle invoked.
  - [ ] MECHANICAL: `--waiting` help text in `_build_parser` (`engine.py:2545-2546`) reads consistently with the chosen interpretation.
  - [ ] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green.
---

# `goc --waiting` filter drifts from the engine on elapsed and bare waits

## Location

- Filter: `goc/engine.py:2846`
- Authoritative impedance predicate: `goc/engine.py:1752` (`waiting_impedes`)
- Flag help text: `goc/engine.py:2545-2546`

## What's broken

The `--waiting` filter at `engine.py:2845-2846` checks one overlay
field:

```python
if getattr(args, "waiting", False):
    filtered = [t for t in filtered if t.waiting_on is not None]
```

The engine's authoritative `waiting_impedes` predicate at
`engine.py:1752` walks a four-cell matrix over BOTH overlay fields
(`waiting_on` and `waiting_until`) — quoting its docstring:

> A `waiting_on` reason without an elapsed `waiting_until` means the
> block is ongoing (no expected return date, or the date is in the
> future) and the card is hidden from queues.
>
> A `waiting_until` in the future implies a `deferred` wait and
> hides the card until that instant passes.
>
> When `waiting_until` is in the past (elapsed), the card RE-ENTERS the
> queue with no manual action — the elapsed-wait is then surfaced
> separately by `validate_waiting_overlay` as an SLE escalation signal.

| `waiting_on` | `waiting_until`        | engine: impeded?       | `--waiting` says |
|--------------|------------------------|------------------------|------------------|
| set          | absent                 | yes (open-ended)       | yes ✓            |
| set          | future                 | yes                    | yes ✓            |
| set          | **elapsed**            | **no** (resurfaces)    | **yes** ✗        |
| unset        | **future**             | **yes** (deferred)     | **no**  ✗        |
| unset        | elapsed                | no                     | no ✓             |
| unset        | absent                 | no                     | no ✓             |

The flag help text at `engine.py:2545-2546` also frames the flag in
terms of the storage field, not the predicate:

```python
parser.add_argument("--waiting", action="store_true",
                    help="Filter to cards carrying a waiting_on overlay.")
```

So the help text is consistent with the buggy code, not with the
contract everyone else in the codebase uses for "what's impeded."

## Empirical evidence

`reproduce.py` builds a temp deck with one card per matrix cell, runs
`uv run goc --waiting` against it, and compares the output to the set
derived from `waiting_impedes` (via the JSON `ready` field plus the
overlay fields). Output:

```
goc --waiting             : ['a-elapsed-with-reason', 'c-reason-only']
waiting_impedes ground truth: ['b-future-bare-deferral', 'c-reason-only']

false-positive (--waiting includes, engine has resurfaced): ['a-elapsed-with-reason']
false-negative (engine impedes, --waiting omits)         : ['b-future-bare-deferral']

DRIFT REPRODUCED
```

## Why it matters

Three known consumers of impedance information already disagree about
how to compute it — each of them re-derived the predicate from one
input field instead of walking the matrix:

- `session-start` hook `_is_impeded` (fixed in commits c191410 and
  64361be — elapsed handling, full-precision datetime comparison).
- `standup` skill body filter (open card
  [`standup-impeded-filter-drifts-from-engine-on-elapsed-and-bare-waits`](../standup-impeded-filter-drifts-from-engine-on-elapsed-and-bare-waits/)).
- **And the engine itself**, via `goc --waiting` (this card).

That last one is the load-bearing surface: every other consumer that
shells out to `goc --waiting` — skill bodies, scripts, future user
documentation — inherits the drift transitively. Two real symptoms:

1. A card with `waiting_on: external, waiting_until: <past>` shows up
   under `goc --waiting`. A reader assumes it's still parked. Meanwhile
   `goc --ready` / `Skill(pull-card)` will autonomously grab it on the
   next /loop tick because `card_is_ready` (`engine.py:1722`) returns
   True. The two flags lie about each other.
2. A card with only `waiting_until: 2030-01-01` (a bare deferral, no
   reason) does NOT show up under `goc --waiting`. The card is hidden
   from the pull queue and from the board's pullable set, yet the very
   flag named after the overlay can't see it. Workers grep `--waiting`
   for "what's parked", miss it, and the deferral is invisible.

The engine should not be the third consumer that disagrees with its
own predicate. Whatever interpretation `--waiting` is meant to carry,
it should be expressed by calling the function whose job is exactly
that judgment.

## Reachability path

`goc --waiting` is the documented surface that GoC's `--help` output
exposes for "show me impeded cards." Any user reading `goc --help` and
running `goc --waiting` to learn what is parked hits this drift on
real decks — both directions are reachable without contrived input:

- Future deferral with no reason: `goc wait <title> --until <future>`
  with no `--reason` (the CLI permits it; `validate_waiting_overlay`
  doesn't require a reason alongside `waiting_until`).
- Elapsed waits with a reason: any card whose `waiting_until` passes
  while the human is away — the engine has already self-cleared
  it from the pull queue, but the CLI flag does not see the
  resurfacing.

## Decision required

Two credible fixes exist; they differ on what `--waiting` *means*.

### Option A — Align with `waiting_impedes` (impedance semantics)

The flag is a query for "what's currently impeded by an overlay." The
filter and the help text both follow `waiting_impedes`:

```python
if getattr(args, "waiting", False):
    filtered = [t for t in filtered if waiting_impedes(t)]
```

Help text becomes something like:

> Filter to cards with an active impediment overlay (waiting_on or
> deferred `waiting_until`).

Pros: the engine speaks with one voice — `--waiting`, `--ready`, board
markers, and `card_is_ready` all agree. Skill bodies that grep
`--waiting` for "what's parked" get the right answer. The bare-deferral
case becomes visible (it currently is invisible everywhere except the
board's ⏳ marker).

Cons: cards with elapsed `waiting_until` drop out of `--waiting`,
which a reader looking for "show me my stale overlays" will miss. The
SLE escalation surface (`validate_waiting_overlay`) handles that view,
but it's a separate flow.

### Option B — Keep the literal field filter, rename for clarity

The flag is a query for "what cards have a `waiting_on` field set."
The code stays, the help text is sharpened to explicitly describe a
field filter:

> Filter to cards with a `waiting_on` overlay set (regardless of
> whether `waiting_until` has elapsed). For currently-impeded cards
> use `--impeded` (a new flag aligned with `waiting_impedes`).

Then add a separate `--impeded` flag whose body is `[t for t in
filtered if waiting_impedes(t)]`.

Pros: backward-compatible for any script that already shells out to
`--waiting` and expects field-set semantics. Both views are
addressable.

Cons: introduces a new flag for a semantic that arguably should have
been the meaning of the existing one. Users have to remember which is
which.

### Option C — Same as A, plus retain elapsed-overlay surfacing

Align `--waiting` with `waiting_impedes` (as Option A), AND add an
explicit `--waiting-stale` flag (or fold this into `--waiting -v`)
that lists cards whose `waiting_until` has elapsed — the SLE
escalation view, but in CLI flag form rather than via `goc validate`.

### Recommendation

Option A reads as the obvious choice given the engine's own internal
shape — the help text reflects a stale framing of "what an overlay
is" (the original implementation predates the `waiting_until`
addition). But the breaking risk for downstream scripts is unknown,
so the gate is `decision` until the human picks.

## Artifacts

- reproduce.py

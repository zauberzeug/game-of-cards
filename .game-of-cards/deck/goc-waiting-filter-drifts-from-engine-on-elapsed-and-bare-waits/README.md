---
title: goc-waiting-filter-drifts-from-engine-on-elapsed-and-bare-waits
summary: "FIXED IN CODE, AWAITING RATIFICATION. `goc --waiting` used to filter with `t.waiting_on is not None`, disagreeing with the engine's `waiting_impedes` predicate in two cells of the four-cell overlay matrix. Commit 91d40320 (2026-06-24) aligned the flag with the predicate while closing a later, gate-free card for the same defect; commit fd34c7cc then routed it through `live_impeded`. Re-measured 2026-08-24: this card's own reproduce.py now reports zero false positives and zero false negatives, and tests/test_waiting_filter_status_scope.py pins the matrix against the CLI. What remains is only the record — the shipped semantics are this card's Option A, which the card recommended. The gate blocks any autonomous close, so a human `goc decide` is the one action left."
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

Re-resolved at HEAD on 2026-08-24 (every number the original filing carried
had drifted or died):

- Filter: `goc/engine.py:4257` — now `live_impeded(t, include_drafts=...)`
- Live-impediment wrapper: `goc/engine.py:2695` (`live_impeded`)
- Authoritative impedance predicate: `goc/engine.py:2646` (`waiting_impedes`)
- Flag help text: `goc/engine.py:3862`
- Regression coverage: `tests/test_waiting_filter_status_scope.py:91`
  (`test_waiting_matches_impedes_predicate`)

## What was broken, and what the code does now

The `--waiting` filter used to check one overlay field:

```python
if getattr(args, "waiting", False):
    filtered = [t for t in filtered if t.waiting_on is not None]
```

The engine's authoritative `waiting_impedes` predicate (`goc/engine.py:2646`)
walks a matrix over BOTH overlay fields — quoting its docstring:

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

**That code is gone.** `goc/engine.py:4257` now reads:

```python
rows = [t for t in rows if live_impeded(t, include_drafts=include_drafts)]
```

`live_impeded` (`goc/engine.py:2695`) is `waiting_impedes` plus two
exclusions the read surfaces all need (terminal status, draft scaffold), so
the flag and the predicate can no longer disagree. The help text moved with
it (`goc/engine.py:3862`):

```python
parser.add_argument("--waiting", action="store_true",
                    help="Filter to cards with an active impediment overlay "
                         "(a waiting_on reason or an unelapsed waiting_until).")
```

The matrix this card was filed on now agrees in every cell:

| `waiting_on` | `waiting_until`        | engine: impeded?       | `--waiting` says | at filing |
|--------------|------------------------|------------------------|------------------|-----------|
| set          | absent                 | yes (open-ended)       | yes ✓            | yes ✓     |
| set          | future                 | yes                    | yes ✓            | yes ✓     |
| set          | **elapsed**            | **no** (resurfaces)    | **no** ✓         | yes ✗     |
| unset        | **future**             | **yes** (deferred)     | **yes** ✓        | no ✗      |
| unset        | elapsed                | no                     | no ✓             | no ✓      |
| unset        | absent                 | no                     | no ✓             | no ✓      |

## Empirical evidence

This card's own `reproduce.py`, re-run at HEAD on 2026-08-24:

```
goc --waiting             : ['b-future-bare-deferral', 'c-reason-only']
waiting_impedes ground truth: ['b-future-bare-deferral', 'c-reason-only']

false-positive (--waiting includes, engine has resurfaced): []
false-negative (engine impedes, --waiting omits)         : []

(unexpected — investigate)
```

Both drift directions are empty. The script still exits 1, because it was
written to assert `DRIFT REPRODUCED` and has no success branch — its exit
code is inverted relative to DoD item 1, which asks it to exit zero when the
output matches. That is a defect in the witness, not in the engine; the two
title lists above are the measurement, and they are identical.

`tests/test_waiting_filter_status_scope.py` independently pins the two cells
this card named, driving the real CLI over a temp deck:
`test_waiting_matches_impedes_predicate` asserts `bare-deferral` IS returned
and `elapsed-wait` is NOT.

## Who fixed it, and when

Commit `91d40320` (2026-06-24) — *"fix(engine): align goc --waiting with the
waiting_impedes predicate"* — closed
[goc-waiting-flag-omits-deferral-cards-it-hides-from-the-queue](../goc-waiting-flag-omits-deferral-cards-it-hides-from-the-queue/),
a card filed at `human_gate: none` on 2026-06-24 and closed the same day for
the same defect this card had been describing since 2026-05-29. Commit
`fd34c7cc` (2026-07-27) then extracted `live_impeded` and routed the flag
through it. Neither commit referenced this card, and no supersession edge was
written, so this card has advertised a fixed defect for 61 days. That
accumulation pattern is filed separately as
[parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them](../parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them/).

## Why it mattered

Three known consumers of impedance information each re-derived the predicate
from one input field instead of walking the matrix:

- `session-start` hook `_is_impeded` (fixed in commits c191410 and
  64361be — elapsed handling, full-precision datetime comparison).
- `standup` skill body filter (open card
  [`standup-impeded-filter-drifts-from-engine-on-elapsed-and-bare-waits`](../standup-impeded-filter-drifts-from-engine-on-elapsed-and-bare-waits/)).
- **And the engine itself**, via `goc --waiting` (this card — since fixed).

That last one was the load-bearing surface: every other consumer that shells
out to `goc --waiting` — skill bodies, scripts, user documentation —
inherited the drift transitively. Both symptoms are now gone:

1. A card with `waiting_on: external, waiting_until: <past>` used to show up
   under `goc --waiting` while `goc --ready` would autonomously grab it,
   so the two flags lied about each other. It is now excluded.
2. A card with only `waiting_until: 2030-01-01` (a bare deferral, no reason)
   used to be invisible to the flag named after the overlay. It is now
   returned.

The principle the fix settled: `--waiting` is expressed by calling the
function whose job is exactly that judgment, rather than restating it.
The `standup` sibling above is still open, so the drift class is not
retired — only the engine's own copy of it.

## Reachability path

`goc --waiting` is the documented surface that GoC's `--help` output exposes
for "show me impeded cards", and both drift directions were reachable
without contrived input — a `goc wait <title> --until <future>` with no
`--reason`, and any card whose `waiting_until` passed while the human was
away. Kept here because it is the reachability record for the closed defect,
and because it is the input shape a ratifying reader should re-run.

## Decision required") is recorded in `log.md` with the principle invoked.
  - [ ] MECHANICAL: `--waiting` help text in `_build_parser` (`engine.py:2545-2546`) reads consistently with the chosen interpretation.
  - [ ] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green.
---

# `goc --waiting` filter drifts from the engine on elapsed and bare waits

## Location

Re-resolved at HEAD on 2026-08-24 (every number the original filing carried
had drifted or died):

- Filter: `goc/engine.py:4257` — now `live_impeded(t, include_drafts=...)`
- Live-impediment wrapper: `goc/engine.py:2695` (`live_impeded`)
- Authoritative impedance predicate: `goc/engine.py:2646` (`waiting_impedes`)
- Flag help text: `goc/engine.py:3862`
- Regression coverage: `tests/test_waiting_filter_status_scope.py:91`
  (`test_waiting_matches_impedes_predicate`)

## What was broken, and what the code does now

The `--waiting` filter used to check one overlay field:

```python
if getattr(args, "waiting", False):
    filtered = [t for t in filtered if t.waiting_on is not None]
```

The engine's authoritative `waiting_impedes` predicate (`goc/engine.py:2646`)
walks a matrix over BOTH overlay fields — quoting its docstring:

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

**That code is gone.** `goc/engine.py:4257` now reads:

```python
rows = [t for t in rows if live_impeded(t, include_drafts=include_drafts)]
```

`live_impeded` (`goc/engine.py:2695`) is `waiting_impedes` plus two
exclusions the read surfaces all need (terminal status, draft scaffold), so
the flag and the predicate can no longer disagree. The help text moved with
it (`goc/engine.py:3862`):

```python
parser.add_argument("--waiting", action="store_true",
                    help="Filter to cards with an active impediment overlay "
                         "(a waiting_on reason or an unelapsed waiting_until).")
```

The matrix this card was filed on now agrees in every cell:

| `waiting_on` | `waiting_until`        | engine: impeded?       | `--waiting` says | at filing |
|--------------|------------------------|------------------------|------------------|-----------|
| set          | absent                 | yes (open-ended)       | yes ✓            | yes ✓     |
| set          | future                 | yes                    | yes ✓            | yes ✓     |
| set          | **elapsed**            | **no** (resurfaces)    | **no** ✓         | yes ✗     |
| unset        | **future**             | **yes** (deferred)     | **yes** ✓        | no ✗      |
| unset        | elapsed                | no                     | no ✓             | no ✓      |
| unset        | absent                 | no                     | no ✓             | no ✓      |

## Empirical evidence

This card's own `reproduce.py`, re-run at HEAD on 2026-08-24:

```
goc --waiting             : ['b-future-bare-deferral', 'c-reason-only']
waiting_impedes ground truth: ['b-future-bare-deferral', 'c-reason-only']

false-positive (--waiting includes, engine has resurfaced): []
false-negative (engine impedes, --waiting omits)         : []

(unexpected — investigate)
```

Both drift directions are empty. The script still exits 1, because it was
written to assert `DRIFT REPRODUCED` and has no success branch — its exit
code is inverted relative to DoD item 1, which asks it to exit zero when the
output matches. That is a defect in the witness, not in the engine; the two
title lists above are the measurement, and they are identical.

`tests/test_waiting_filter_status_scope.py` independently pins the two cells
this card named, driving the real CLI over a temp deck:
`test_waiting_matches_impedes_predicate` asserts `bare-deferral` IS returned
and `elapsed-wait` is NOT.

## Who fixed it, and when

Commit `91d40320` (2026-06-24) — *"fix(engine): align goc --waiting with the
waiting_impedes predicate"* — closed
[goc-waiting-flag-omits-deferral-cards-it-hides-from-the-queue](../goc-waiting-flag-omits-deferral-cards-it-hides-from-the-queue/),
a card filed at `human_gate: none` on 2026-06-24 and closed the same day for
the same defect this card had been describing since 2026-05-29. Commit
`fd34c7cc` (2026-07-27) then extracted `live_impeded` and routed the flag
through it. Neither commit referenced this card, and no supersession edge was
written, so this card has advertised a fixed defect for 61 days. That
accumulation pattern is filed separately as
[parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them](../parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them/).

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

**Reduced to a ratification on 2026-08-24.** The code already implements
Option A: the filter calls the predicate and the help text describes an
active impediment overlay. Nothing here is undecided in the engine — what is
missing is a human's name on the semantics that shipped, which DoD item 3
requires and which no autonomous pass may supply (`goc status ... superseded`
refuses while `human_gate: decision`, pointing at `goc decide`).

The one action left: `goc decide` this card in favour of Option A, then close
it — or, since a later card actually delivered the fix, supersede it via
`goc status <this card> superseded --by goc-waiting-flag-omits-deferral-cards-it-hides-from-the-queue`.
Option B remains on the record below only so that ratifying A is a choice
rather than a default.

Two credible fixes existed; they differed on what `--waiting` *means*.

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

Option A, and it is what shipped. The help text at filing reflected a stale
framing of "what an overlay is" (the original implementation predated the
`waiting_until` addition); commit `91d40320` replaced both the filter and the
help text with the predicate reading. The breaking risk this card flagged as
unknown has since been absorbed in production for 61 days with no reported
fallout, and `tests/test_waiting_filter_status_scope.py` pins the semantics.

## Artifacts

- reproduce.py

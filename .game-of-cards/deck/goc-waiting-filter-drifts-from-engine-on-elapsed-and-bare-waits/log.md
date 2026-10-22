## 2026-08-24 — hygiene pass: the defect is fixed; only the record is missing

Surfaced by the defunct-citation category of a `Skill(refine-deck)` pass, not
by anyone reading the card. All five cites in the original `## Location` had
died — the anchor text of `filtered = [t for t in filtered if t.waiting_on is
not None]` exists nowhere in the tree. Per the skill's rule, an anchor that
exists nowhere means the cited code was refactored away and the card must be
re-read against HEAD.

**Re-measured.** This card's own `reproduce.py` now reports zero false
positives and zero false negatives across the overlay matrix — the two cells
it was filed on both agree. `tests/test_waiting_filter_status_scope.py`
independently pins the same two cells against the real CLI. The `--waiting`
help text now describes the predicate rather than the storage field.

**Who fixed it.** Commit `91d40320` (2026-06-24) aligned `--waiting` with
`waiting_impedes` while closing
`goc-waiting-flag-omits-deferral-cards-it-hides-from-the-queue`, a card filed
at `human_gate: none` that same day for the same defect. Commit `fd34c7cc`
(2026-07-27) then extracted `live_impeded` and routed the flag through it.
Neither referenced this card; no supersession edge was written. This card has
therefore advertised a fixed defect for 61 days.

**Why it is still open.** DoD item 3 asks for the chosen interpretation to be
recorded, and closing requires lowering the gate. `goc status <title>
superseded --by goc-waiting-flag-omits-deferral-cards-it-hides-from-the-queue`
was attempted and the engine refused:

```
ERROR: human_gate is 'decision'; run `goc decide ...` to lower the gate
before closing into 'superseded'.
```

That refusal is correct and is why this card cannot be retired by an
autonomous pass. The README dashboard was rewritten in place — Location
re-resolved, the matrix re-scored with an "at filing" column, the decision
section reduced to a ratification — so the remaining human action is one
command. No code changed.

The generalisable finding (a parked card whose defect is fixed elsewhere is
never re-checked, and structurally cannot be retired without a human) is
filed as `parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them`.

## 2026-08-24T05:12:00Z — Staleness re-check

Fixed by `91d40320` (2026-06-24) closing
[`goc-waiting-flag-omits-deferral-cards-it-hides-from-the-queue`](../goc-waiting-flag-omits-deferral-cards-it-hides-from-the-queue/)
— `goc --waiting` now routes through the `waiting_impedes` predicate instead
of testing `t.waiting_on is not None`, which is exactly the drift this card
reports. `fd34c7cc` (2026-07-27) then extracted `live_impeded` and routed the
flag through it.

Machine-readable restatement of the prose note above, under the greppable
heading `Skill(finish-card)` § "Other cards your fix also fixed" now
prescribes, so a staleness scan can tell a card that was re-read from one
nobody has opened. Retiring this card needs `goc decide`; an agent may not
lower the gate. Tracked by
[`parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them`](../parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them/).

## 2026-09-14 — refine-deck: defunct cite corrected by hand

The body cited `card_is_ready` at `engine.py:1722`. That number was wrong the
day it was written — at this card's filing commit (`5570bdb4`) `card_is_ready`
was at line 1729, and 1722 was a blank line two lines above an unrelated
function. Because the anchored citation recipe compares the anchor line's text
to HEAD's text at the same offset, and both were blank, three consecutive
hygiene passes verdicted the cite `current` while it drifted 910 lines from the
function it names.

Corrected to `goc/engine.py:2632`, the definition of `card_is_ready` in HEAD.
The recipe gap that hid it is filed as
[citation-repair-pass-calls-a-cite-current-when-its-anchor-line-is-a-brace-or-blank](../citation-repair-pass-calls-a-cite-current-when-its-anchor-line-is-a-brace-or-blank/),
which carries this cite as its worked example.

## 2026-05-29T11:35:23Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

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


## 2026-10-22T06:00:43Z: decision recorded

Option A — Align with waiting_impedes (impedance semantics), ratified as shipped in 91d40320 — Stale sweep under the bulk rule the maintainer approved in a human session on 2026-10-22: the card was reduced to a ratification of the shipped Option A; principle: a CLI view must ask the engine predicate (waiting_impedes via live_impeded) instead of re-deriving it from one field. Gate decision → none.

## 2026-10-22T06:01:12Z — Closure

- **What changed**: no engine change — Option A shipped in 91d40320 and was routed through `live_impeded` in fd34c7cc; this closure ratifies it. `reproduce.py` now encodes the post-fix contract (exit 0 when `--waiting` equals `waiting_impedes` across the matrix) instead of exiting 0 only while the drift fires. The README body is repaired: the 2026-08-24 hygiene pass had split it at the `## Decision required` text inside the frontmatter's DoD line, leaving a stale second copy of the old body (155 lines) after a glued DoD fragment; that block is removed and the ratification section kept.
- **Verification**: `reproduce.py` → both difference sets empty, exit 0. `tests/test_waiting_filter_status_scope.py::test_waiting_matches_impedes_predicate` pins the matrix against the CLI flag. The `--waiting` help text reads "an active impediment overlay (a waiting_on reason or an unelapsed waiting_until)", which matches Option A.
- **Audit**: no rubric configured; principle invoked: a CLI view asks the engine predicate instead of re-deriving it from one field.
- **Project impact**: n/a
- **Tests**: 1349 passed / 0 failed on the merged main (2026-10-22).

## Closure verification (2026-10-22T06:01:12Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-10-22 — Closure' present

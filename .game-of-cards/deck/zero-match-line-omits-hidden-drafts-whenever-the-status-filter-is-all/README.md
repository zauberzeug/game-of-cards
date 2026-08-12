---
title: zero-match-line-omits-hidden-drafts-whenever-the-status-filter-is-all
summary: "The zero-match queue line only recounts hidden drafts when the status filter is not `all`, on the premise that `--status all` does not exclude drafts. That is true of `filter_cards` alone, but `card_is_ready` and `live_impeded` each carry their own draft conjunct that stays live at `all` — and `--waiting`, `--closed-since` and `--board` auto-extend an unset status to `all`. So plain `goc --waiting` prints the drained-deck sentence while hiding an impeded scaffold that publishing would reveal, the exact collapse the clause exists to undo."
status: done
stage: null
contribution: medium
created: "2026-08-12T04:57:03Z"
closed_at: "2026-08-12T05:06:02Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits non-zero — plain `goc --waiting` and
        `goc --ready --status all` both name the scaffold they are hiding,
        matching what the same decks print under `--status open`
  - [x] TDD: a regression test in `tests/test_empty_query_result_line.py` pins
        both shapes with the status filter LEFT UNSET (the predecessor's cases
        all pass `status_flag="open"`, which is why this survived), plus the
        true-negative control that `--status all` alone still gains no clause
  - [x] MECHANICAL: the recount's entry condition no longer names a single
        conjunct — `filter_cards`' draft gate is one of three axes, so the
        guard must not claim to know from `status` alone that nothing was hidden
  - [x] TDD: existing pins in `tests/test_empty_query_result_line.py` stay green
        (plain `goc`, `--ready`, `--json`, `--board`, the two `--waiting` and two
        `--closed-since` counterfactual halves, and every user-supplied filter
        still named)
  - [x] MECHANICAL: plugin mirrors re-synced so the four `engine.py` copies stay
        byte-identical
  - [x] PROCESS: guard sensitivity confirmed — reverting the fix turns the new
        test red, recorded in `log.md`
worker: {who: "claude[bot]", where: main}
---

# The hidden-draft clause goes missing exactly where the status filter is `all`

`goc` tells the reader how many unauthored scaffolds a zero-match query is
withholding, and points at `goc publish` as the way to see them. On any query
whose status filter resolves to `all` it says nothing — including the plain,
flagless `goc --waiting`, where the status filter is `all` because the engine
put it there.

## Location

Line numbers are **post-fix**; the pre-fix shape is quoted inline.

- `goc/engine.py:4095` — the recount's entry condition in `_cmd_default`,
  which read:

  ```python
  if not filtered and status != "all":
      hidden_drafts = len(
          [t for t in run_query(include_drafts=True) if card_is_draft(t)]
      )
  ```

- `goc/engine.py:3980-3988` — where an unset `--status` becomes `all`:

  ```python
  status = (
      "all"
      if (
          closed_since_threshold is not None
          or getattr(args, "waiting", False)
          or args.board
      )
      else "open"
  )
  ```

- `goc/engine.py:2822` — the `filter_cards` draft conjunct the guard is
  reasoning about, and the only one that really is inert at `all`.
- `goc/engine.py:2485` (`card_is_ready`) and `goc/engine.py:2600`
  (`live_impeded`) — the two draft conjuncts that are **not** inert at `all`.
- `goc/engine.py:3603` — `render_empty_query_line`, which renders whatever
  count it is handed (unchanged by this card).

## What's broken

The recount answers a counterfactual: *would this card appear if its draft
flag were cleared?* Its entry guard was an optimization — skip the second
pass when the draft gate could not have removed anything. The comment above
it stated the premise:

> ```
> # The draft conjunct is recovered only on the empty path — the normal
> # query stays one pass — and only when it could have applied at all
> # (`--status all` does not exclude drafts, so nothing was hidden).
> ```

`--status all` does not exclude drafts *in `filter_cards`*. But
`_cmd_default` narrows in three stages, and the closure that runs them
(`run_query`, `goc/engine.py:4000`) documents that the draft gate lives on
three separate axes:

> ```
> # `include_drafts` is threaded to every axis the draft gate is inlined
> # on: `filter_cards`' own conjunct, `card_is_ready` (via it), and
> # `live_impeded`.
> ```

`card_is_ready` and `live_impeded` never look at the status filter — they
drop drafts unconditionally. So under `--ready` or `--waiting`, drafts stay
hidden at `--status all`, and the guard suppressed the very count that would
have said so.

The predecessor card
[zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface](../zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface/)
fixed the *body* of the recount to replay all three stages. Its entry
condition was left keyed to the first stage alone, so the pass it fixed is
never reached on these queries.

Two shapes are reachable, and the `--waiting` one is the **default
invocation**: `goc --waiting` with no `--status` at all resolves to `all` by
the branch quoted above.

## Empirical evidence

`reproduce.py` exits 0 while the defect is present and 1 once it is fixed.
Both pairs it prints are the **same deck** rendered twice, so the two halves
are directly comparable: widening a filter cannot make a hidden card less
hidden, so the renderings must agree.

Before the fix — the `--status open` half prints the clause, widening to
`all` deletes it:

```
shape 1 — an impeded draft, queried two ways
  goc --waiting --status open : No cards match (status: open; waiting: active impediment overlay; 1 unauthored draft scaffold hidden — author, then `goc publish <title>`).
  goc --waiting               : No cards match (status: all; waiting: active impediment overlay).
  ...after `goc publish`      : alpha  open    medium    3.0  none  bug   0/1

shape 2 — a queueable draft, queried two ways
  goc --ready                 : No cards match (ready: status open, gate none, no active impediment; 1 unauthored draft scaffold hidden — author, then `goc publish <title>`).
  goc --ready --status all    : No cards match (ready: status open, gate none, no active impediment; status: all).

[DEFECT] adding `--status all` (or letting --waiting resolve it) silently drops a true hidden-draft clause
```

The third line is the discriminator that makes the omission a false negative
rather than a correctly-withheld clause: publishing the scaffold makes the
identical default query list it.

After the fix (exit 1) — both halves of both pairs agree:

```
shape 1 — an impeded draft, queried two ways
  goc --waiting --status open : No cards match (status: open; waiting: active impediment overlay; 1 unauthored draft scaffold hidden — author, then `goc publish <title>`).
  goc --waiting               : No cards match (status: all; waiting: active impediment overlay; 1 unauthored draft scaffold hidden — author, then `goc publish <title>`).
  ...after `goc publish`      : alpha  open    medium    3.0  none  bug   0/1

shape 2 — a queueable draft, queried two ways
  goc --ready                 : No cards match (ready: status open, gate none, no active impediment; 1 unauthored draft scaffold hidden — author, then `goc publish <title>`).
  goc --ready --status all    : No cards match (ready: status open, gate none, no active impediment; status: all; 1 unauthored draft scaffold hidden — author, then `goc publish <title>`).
```

## Why it matters

The clause exists to separate three states that used to render
byte-identically: a drained deck, a filter no card satisfies, and a deck of
scaffolds nobody has authored yet. Omitting it re-collapses the third into
the first — the reader is told the query found nothing, with no hint that
`goc publish` is one command away from a non-empty answer.

`goc --waiting` is the shape that matters most. It is the impediment review
surface: a human or `Skill(standup)` asking "what is stuck?". A scaffold
carrying an overlay is precisely the card that should not be forgotten, and
it is invisible on the surface built to surface it — with the flagless
invocation, so no reader is doing anything unusual to trigger it.

The mirror-image failure is already carded and closed, which is what makes
the omission concrete rather than theoretical: the predecessor removed
*false positives* from this same count, and its regression tests all pass
`status_flag="open"` explicitly (`tests/test_empty_query_result_line.py:457`,
`:464`, `:471`), so nothing exercised the status the command line actually
resolves to.

Related, not duplicated:
[draft-gating-is-opt-in-per-surface-and-new-verbs-keep-missing-it](../draft-gating-is-opt-in-per-surface-and-new-verbs-keep-missing-it/)
is the umbrella for the inlined draft gate, and its "the cost is now
symmetric" section already names the three-axis threading this card trips
over. This is not a seventh instance of "a surface forgot to exclude drafts",
and it adds no fourth `include_drafts` site — it removes a stale conditional.
The fix below stands whichever mechanism that card's decision picks.

## Fix (applied)

The `status != "all"` half of the entry guard is gone from `_cmd_default`
(`goc/engine.py:4095`):

```python
hidden_drafts = 0
if not filtered:
    hidden_drafts = len(
        [t for t in run_query(include_drafts=True) if card_is_draft(t)]
    )
```

The recount was already exact — it replays the whole query and counts only
cards the draft flag alone is hiding — so the guard was never load-bearing
for correctness, only for skipping a second pass. Removing it is safe by the
recount's own construction: it runs only when `filtered` is empty, and when
`status == "all"` with no draft-gated stage active,
`run_query(include_drafts=True)` returns that same empty set, so the count is
`0` and the clause stays absent. The comment above the guard lost the
`--status all` justification with it — that sentence was the defect, restated
— and now says why the recount needs no `status` guard at all, so the next
reader does not re-derive the same wrong shortcut.

Cost: one extra `run_query` pass on `--status all` queries that matched
nothing, the same pass every other empty query already pays.

`tests/test_empty_query_result_line.py` gained
`HiddenDraftCountSurvivesStatusAllTest`: three positives that leave the
status filter where the command line leaves it (flagless `--waiting`,
`--waiting --status all` paired against `--status open`, `--ready --status
all` paired against plain `--ready`), and three negatives that stop the fix
from degenerating into "always count under `all`" — an unimpeded draft under
flagless `--waiting`, `--status all` with no draft-gated stage active, and
the two flagless `--waiting` shapes asserted non-identical.

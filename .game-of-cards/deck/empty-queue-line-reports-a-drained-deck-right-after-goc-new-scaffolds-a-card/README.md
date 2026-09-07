---
title: empty-queue-line-reports-a-drained-deck-right-after-goc-new-scaffolds-a-card
summary: "The zero-match queue message enumerates every user-supplied filter but never the draft exclusion filter_cards applies on its own, so a deck whose only open cards are unauthored goc new scaffolds prints \"No cards match (status: open).\" — the exact drained-queue sentence a truly empty deck prints. goc --status all on the same deck lists those cards as status: open and the board marks them, so the table path contradicts its own siblings on the very first thing a new user does."
status: done
stage: null
contribution: medium
created: "2026-08-11T04:51:17Z"
closed_at: "2026-08-11T04:58:02Z"
human_gate: none
advances:
  - query-flag-validation-is-opt-in-per-flag-and-new-flags-keep-missing-it
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — a deck of unauthored scaffolds no
        longer prints the drained-deck sentence verbatim
  - [x] TDD: a regression test pins that the draft conjunct is named with its
        count when drafts were dropped, and that a genuinely empty deck (and a
        deck whose visible cards were dropped by a user filter) gains NO draft
        clause — the message must not grow a always-on conjunct
  - [x] TDD: existing pins in `tests/test_empty_query_result_line.py` stay green
        (`--json` still `[]`, `--board` still header-only, non-empty tables
        unchanged, every user-supplied filter still named)
  - [x] MECHANICAL: plugin mirrors re-synced so the four `engine.py` copies stay
        byte-identical
  - [x] PROCESS: guard sensitivity confirmed — reverting the fix turns the new
        test red, recorded in `log.md`
worker: {who: "claude[bot]", where: main}
---

# The zero-match queue line calls a deck of fresh scaffolds a drained deck

`goc` prints the same sentence for "this deck has no cards" and "this deck's
only cards are the ones you just created" — so the first thing a new user
does after `goc new` reports that nothing exists.

## Location

`goc/engine.py:3502-3565` — `render_empty_query_line`. The predicate it
enumerates omits the draft conjunct applied in `filter_cards`
(`goc/engine.py:2794-2795`). Mirrored byte-for-byte in
`claude-plugin/goc/engine.py`, `codex-plugin/goc/engine.py`,
`openclaw-plugin/goc/engine.py`.

## What's broken

`filter_cards` drops unauthored scaffolds from **every** status filter except
`all`, unconditionally and without any flag asking it to
(`goc/engine.py:2794-2795`):

```python
if status != "all":
    out = [t for t in out if not card_is_draft(t)]
```

`render_empty_query_line` then explains the zero-match result by listing the
filters — but only the ones the caller passed on the command line
(`goc/engine.py:3538-3564`): `ready`, `status`, `waiting`, `stage`,
`contribution`, `gate`, `since`, `closed-since`, `advances`, `advanced-by`,
`tag`, `worker`. The draft conjunct is not among them, so a result emptied
*entirely* by the draft filter is attributed to `status: open`.

That contradicts the function's own stated contract
(`goc/engine.py:3503`):

> State that a queue query matched nothing, **naming the filters in effect**.

and the reason the function exists at all (`goc/engine.py:3509-3511`):

> Three different states then rendered byte-identically: a genuinely drained
> queue, a filter no card satisfies, and a mistyped `--worker` value.

There is a fourth state, and it is the one a first-time user hits. It renders
byte-identically to the first.

The rest of the CLI does not have this gap. The board path already has the
vocabulary — `render_board` marks a draft `✎` rather than hiding it — and
`--status all` lists the cards outright, so two adjacent read surfaces
contradict the table path about whether the deck is empty.

## Empirical evidence

`uv run python .game-of-cards/deck/empty-queue-line-reports-a-drained-deck-right-after-goc-new-scaffolds-a-card/reproduce.py`:

```
deck A — no card directories at all
  goc  -> 'No cards match (status: open).'

deck B — two `goc new` scaffolds, both `status: open`
  cards on disk       : ['alpha-card', 'beta-card']
  their status values : [('alpha-card', 'open'), ('beta-card', 'open')]
  card_is_draft       : [True, True]
  goc  -> 'No cards match (status: open).'

messages identical: True

FAIL: a deck with two open cards prints the drained-deck sentence verbatim;
the draft conjunct that emptied the result is never named.
```

Reproduced end-to-end through the real CLI on a scratch repo, which is the
path a consumer actually walks:

```
$ goc new alpha-card --summary "Alpha."
created .game-of-cards/deck/alpha-card/
$ goc new beta-card --summary "Beta."
created .game-of-cards/deck/beta-card/
$ goc
No cards match (status: open).
$ goc --status all
TITLE       STATUS  CONTR.  VALUE  GATE      TAGS  DOD
----------  ------  ------  -----  --------  ----  ---
alpha-card  open    medium    3.0  decision        0/1
beta-card   open    medium    3.0  decision        0/1
```

## Why it matters

The draft flag is a deliberate protection: a half-written scaffold stays out
of the queue until it is authored. Hiding it is correct. Hiding it *silently*
is not, and the cost lands on exactly the reader least able to absorb it.

- **First-run confusion.** `goc install` → `goc new my-first-card` → `goc` is
  the shortest path through the tool, and it ends in a message stating the
  card is not there. Nothing in the output points at authoring or
  `goc publish`, so the natural conclusion is that `goc new` failed.
- **The queue is the autonomous loop's only input.** `Skill(pull-card)` and
  `Skill(next-card)` both read this surface and both treat a zero-match result
  as "queue empty" — the branch that diverts a session into `Skill(audit-deck)`
  to file *more* cards. A deck of unauthored scaffolds is not a drained deck,
  and a run that reads it as one files new work while authored-but-unpublished
  work sits invisible.
- **It is the same defect the surface was built to fix.** Two closed siblings
  already taught this line to distinguish states it was collapsing:
  [empty-queue-view-prints-nothing-instead-of-saying-no-cards-match](../empty-queue-view-prints-nothing-instead-of-saying-no-cards-match/)
  gave it a sentence at all, and
  [empty-result-line-reports-a-drained-ready-queue-that-still-has-cards](../empty-result-line-reports-a-drained-ready-queue-that-still-has-cards/)
  made `--ready` add a conjunct instead of replacing one. Both closed by
  naming a conjunct that was in effect but unstated. This is the third, and
  the only one whose conjunct no flag can reveal.

Distinct from
[draft-gating-is-opt-in-per-surface-and-new-verbs-keep-missing-it](../draft-gating-is-opt-in-per-surface-and-new-verbs-keep-missing-it/),
which collects surfaces that *fail* to gate drafts (`quality-pass` audits
them, `decide` lowers their gate, `triage` listed them). This surface gates
drafts correctly; it just does not disclose that it did. Opposite direction,
different fix, so it is filed against the reporting family rather than as a
fourth instance of the gating family.

## Fix (landed)

`render_empty_query_line` is given the one input it cannot read off `args` —
how many drafts the query dropped — and names that conjunct when it is
non-zero. All in `goc/engine.py`:

1. `filter_cards` — new `include_drafts: bool = False` keyword suppressing the
   `card_is_draft` conjunct. No existing caller changes behavior; it exists so
   the count can be recovered without restating the predicate.
2. `card_is_ready` — the same keyword, threaded from `filter_cards`, gating
   only its own `card_is_draft` clause. Required, and not anticipated when this
   card was filed: readiness drops drafts on a *second*, independent axis, so
   suppressing the conjunct in `filter_cards` alone left `--ready` — the
   pull-card / next-card surface, the costly one — still reading a deck of
   scaffolds as a drained queue. Default keeps readiness itself unchanged, so
   the `card_is_workable_for_scheduler` coupling invariant is untouched.
3. `_cmd_default` — on the empty path only (and only when `status != "all"`,
   which excludes nothing), re-run `filter_cards` with `include_drafts=True`
   and count the drafts. The normal non-empty query stays at one pass.
4. `render_empty_query_line` — accepts `hidden_drafts: int = 0` and appends
   `N unauthored draft scaffold(s) hidden — author, then \`goc publish <title>\``
   when non-zero, pluralized through `_plural`.

Counting rather than always stating the conjunct is what separates the two
states: an unconditional "excludes drafts" clause would still render
identically on a drained deck — the exact collapse this surface exists to
undo.

Post-fix, the two decks the reproduce script builds are distinguishable:

```
deck A — no card directories at all
  goc  -> 'No cards match (status: open).'

deck B — two `goc new` scaffolds, both `status: open`
  goc  -> 'No cards match (status: open; 2 unauthored draft scaffolds hidden
           — author, then `goc publish <title>`).'

messages identical: False
PASS
```

and the `--ready` surface names it too, without inventing a clause where the
gate (not the draft flag) is what emptied the queue:

```
$ goc --ready          # one gate-none draft scaffold
No cards match (ready: status open, gate none, no active impediment;
                1 unauthored draft scaffold hidden — author, then `goc publish <title>`).
$ goc --tag infra      # drafts do not match the tag either — no draft clause
No cards match (status: open; tag: infra).
```

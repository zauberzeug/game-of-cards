---
title: triage-empty-line-omits-the-worker-filter-and-hidden-drafts-it-dropped
summary: "goc triage prints the fixed sentence \"No parked cards (gate ≠ none).\" whenever its result is empty, naming neither the --worker filter it matched on nor the unauthored draft scaffolds it dropped. On a deck with 184 parked cards, goc triage --worker nobody reports that none exist; right after goc new scaffolds a gated card, triage reports an empty park queue while the queue table's own zero-match line names both conjuncts."
status: done
stage: null
contribution: medium
created: "2026-08-19T05:06:15Z"
closed_at: "2026-08-19T05:14:54Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits non-zero — `goc triage`'s empty line names the `--worker` value, the hidden-draft count, and the `status: open` conjunct
  - [x] TDD: regression test asserts the empty line echoes an unmatched `--worker` value verbatim and counts dropped drafts, and that a non-empty triage render is unchanged
  - [x] MECHANICAL: `render_empty_query_line`'s docstring no longer cites `goc triage` as a surface that already states its zero-match predicate
worker: {who: "claude[bot]", where: main}
---

# triage-empty-line-omits-the-worker-filter-and-hidden-drafts-it-dropped

`goc triage` answers "what is waiting on me?". When the answer is empty it
prints one fixed sentence that names one of the four conjuncts that produced
it, so three different deck states render byte-identically: a genuinely empty
park queue, a mistyped `--worker` value, and a deck whose parked cards are all
unauthored `goc new` scaffolds.

## Location

`goc/engine.py:6750-6792` (`_cmd_triage`). The predicate is four conjuncts
wide plus an optional filter:

```python
all_cards = [
    t
    for t in load_all_cards()
    if t.status == "open" and t.human_gate != "none" and not card_is_draft(t)
]
if worker:
    needle = worker.lower()
    cards = [t for t in all_cards if needle in _worker_who(t.frontmatter.get("worker")).lower()]
```

and the zero-match report is a constant:

```python
if not payload:
    print("No parked cards (gate ≠ none).")
    return
```

## What's broken

The sentence names `gate != none` and nothing else. `status == "open"`, the
`card_is_draft` drop, and the `--worker` substring match are all invisible.

The contract it violates is written down in this same module, in the docstring
of `render_empty_query_line` (`goc/engine.py:3655-3681`) — the helper the queue
table routes its own zero-match line through. That docstring cites `goc triage`
as a surface that already does the right thing:

> `render_table` returns "" for an empty card list, so without this the
> table path is the one read surface that cannot express "the query ran and
> matched nothing" — `goc triage` prints a sentence, `--json` prints `[]`
> and `--board` prints its column header [...]

and then gives the precise reason a sentence is not enough on its own:

> That last one is why the message enumerates the predicate rather than
> just saying "no cards". `--status` and `--tag` reject unknown values at
> parse time, but `worker` is deliberately unregistered (any person slug,
> machine name or capability tag is legal), so there is no enum to validate
> a typo against and echoing the filter back is the only available signal.

`goc triage` takes `--worker` (`goc/engine.py:4004`) — the one unregistered
free-form filter that argument is about — and echoes nothing. The helper is
called from exactly one site (`goc/engine.py:4242`, `_cmd_default`); triage is
the only other filtered read surface in the engine that reports a zero match,
and it is the only one still doing it with a constant. `quality-pass` states
its count and filter (`Quality pass over 0 cards (status=done):`), `validate`
was given the same treatment by
[goc-validate-reports-a-clean-pass-when-it-validated-no-cards](../goc-validate-reports-a-clean-pass-when-it-validated-no-cards/),
and `repair-edges` / `migrate` take no filters, so they have nothing to
disclose.

## Empirical evidence

`uv run python .game-of-cards/deck/triage-empty-line-omits-the-worker-filter-and-hidden-drafts-it-dropped/reproduce.py`:

```
deck: 2 cards, 2 parked (gate != none), 1 of them unauthored drafts

triage on a deck whose only parked cards are `goc new` scaffolds:
  triage : No parked cards (gate ≠ none).
  queue  : No cards match (status: open; gate: decision; 2 unauthored draft scaffolds hidden — author, then `goc publish <title>`).

triage --worker nobdy (a typo for 'rodja'; both cards are worker: rodja):
  triage : No parked cards (gate ≠ none).
  queue  : No cards match (status: open; gate: decision; worker: 'nobdy'; 1 unauthored draft scaffold hidden — author, then `goc publish <title>`).

DEFECT: triage's empty line does not echo the --worker value that emptied it
DEFECT: triage's empty line does not count the unauthored draft scaffolds it dropped
DEFECT: triage reports a drained park queue right after `goc new` scaffolds gated cards
```

Against this repo's own deck, which has 184 parked cards:

```
$ goc triage --worker nobody
No parked cards (gate ≠ none).
```

## Why it matters

`goc triage` is the human's read of the Andon cord — the surface that says
whether any card is parked waiting on a person. A false "nothing is waiting on
you" is the one wrong answer this verb must not give, because the reader's next
action is to stop looking.

Two reachable paths produce it:

1. **Runner-scoped triage with a typo.** `AGENTS.md` documents
   `goc --worker <X>` and `GOC_WORKER` as the runner-specific queue view, so
   `goc triage --worker $GOC_WORKER` is the natural per-runner park check. The
   `worker` value is deliberately unregistered, so a typo cannot be rejected at
   parse time and is reported as a drained queue instead.
2. **Right after `goc new`.** A scaffold is born `draft: true` and
   `human_gate: decision`. Until it is authored it is a parked card that triage
   drops silently — the shortest path through the tool (`goc new --gate
   decision` → `goc triage`) ends in "nothing is waiting on you" about the card
   just filed. This is the same symptom
   [empty-queue-line-reports-a-drained-deck-right-after-goc-new-scaffolds-a-card](../empty-queue-line-reports-a-drained-deck-right-after-goc-new-scaffolds-a-card/)
   fixed for the queue table; triage was not part of that change.

The draft-hiding itself is correct and deliberate — it was added by
[goc-triage-lists-unauthored-draft-scaffolds-as-parked-cards](../goc-triage-lists-unauthored-draft-scaffolds-as-parked-cards/).
This card is about disclosing the drop, not undoing it, and so is distinct from
[draft-gating-is-opt-in-per-surface-and-new-verbs-keep-missing-it](../draft-gating-is-opt-in-per-surface-and-new-verbs-keep-missing-it/),
which tracks surfaces that fail to apply the draft filter at all.

`--json` is unaffected: it prints `[]`, which is self-describing.

## Fix (landed)

`render_empty_triage_line(worker, hidden_drafts)` (`goc/engine.py`) replaces the
constant, building the sentence from the predicate, the quoted `--worker` value,
and the hidden-draft count with its `goc publish` next step:

```
No parked cards (status: open; gate ≠ none; worker: 'nobdy').
No parked cards (status: open; gate ≠ none; 2 unauthored draft scaffolds hidden — author, then `goc publish <title>`).
```

`_cmd_triage` now applies `--worker` **before** splitting drafts off, so
`hidden_drafts` is the number `goc publish` would actually surface *in this
view* — a draft the worker filter also excludes is not disclosed. That is the
lesson of
[zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface](../zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface/),
applied here from the start rather than as a follow-up. The count comes off the
load `_cmd_triage` already performs; the deck is not walked twice.

The draft clause itself moved into `_hidden_drafts_clause`, shared with
`render_empty_query_line`, so the count, the noun and the next step cannot
drift between the two surfaces. `render_empty_query_line`'s docstring no longer
implies triage was already doing this.

`status: open` is disclosed, not changed: whether triage should surface cards
parked at `active` is the open decision on
[parked-active-cards-are-missing-from-goc-triage](../parked-active-cards-are-missing-from-goc-triage/).
Naming the conjunct is what makes today's behaviour legible while that is
pending. `--json` still prints exactly `[]`.

`tests/test_triage_empty_line.py` (13 tests) locks all of it, including both
directions of the worker-scoped count and the unchanged non-empty render.
Against the pre-fix engine it produces 8 failures + 2 errors.

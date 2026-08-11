---
title: zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface
summary: "The zero-match queue line's hidden-draft count replays only filter_cards, not the --closed-since and --waiting conjuncts _cmd_default applies after it, so `goc --waiting --status open` and `goc --closed-since 1h --status done` report drafts as hidden from queries those drafts would not match even once published. live_impeded carries a third inlined draft conjunct that the predecessor card's include_drafts thread never reached, so under --waiting the count cannot be evaluated counterfactually at all. The clause exists to separate a drained deck from a deck of scaffolds; miscounted, it sends the reader to `goc publish` for nothing."
status: active
stage: null
contribution: medium
created: "2026-08-11T05:24:17Z"
closed_at: null
human_gate: none
advances:
  - query-flag-validation-is-opt-in-per-flag-and-new-flags-keep-missing-it
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — neither the no-overlay draft under
        `--waiting` nor the long-closed draft under `--closed-since` produces a
        hidden-draft clause, and the impeded-draft control still does
  - [ ] TDD: a regression test in `tests/test_empty_query_result_line.py` pins
        both false-positive shapes AND the two true-positive controls (a draft
        the `--waiting` query really is hiding, a draft inside the
        `--closed-since` window), so the fix cannot be "never count under those
        flags"
  - [ ] MECHANICAL: the recount evaluates the draft conjunct counterfactually on
        every axis it is inlined on — `filter_cards`, `card_is_ready` and
        `live_impeded` — rather than only the first two
  - [ ] TDD: existing pins in `tests/test_empty_query_result_line.py` stay green
        (plain `goc`, `--ready`, `--json`, `--board`, non-empty tables, and every
        user-supplied filter still named)
  - [ ] MECHANICAL: plugin mirrors re-synced so the four `engine.py` copies stay
        byte-identical
  - [ ] PROCESS: guard sensitivity confirmed — reverting the fix turns the new
        test red, recorded in `log.md`
worker: {who: "claude[bot]", where: main}
---

# The hidden-draft clause names drafts that publishing would not surface

`goc` tells the reader that unauthored scaffolds are being withheld from a
query, and points at `goc publish` as the way to see them — on queries where
publishing them changes nothing, because a *different* filter excludes them.

## Location

- `goc/engine.py:4042-4061` — the `hidden_drafts` recount in `_cmd_default`.
- `goc/engine.py:4000-4005` — the `--closed-since` window, applied *after*
  `filter_cards` and never replayed by the recount.
- `goc/engine.py:4006-4016` — the `--waiting` narrowing, same.
- `goc/engine.py:2585-2589` — `live_impeded`, which carries its own
  `not card_is_draft(card)` conjunct.
- `goc/engine.py:3590-3594` — `render_empty_query_line`, which emits the clause.

## What's broken

`_cmd_default` narrows the deck in **three** stages. `filter_cards` runs first
(`engine.py:3986`), then two more conjuncts run on the result:

```python
if closed_since_threshold is not None:
    filtered = [
        t for t in filtered
        if (dt := _closed_at_instant(t.closed_at)) is not None
        and dt >= closed_since_threshold
    ]
if getattr(args, "waiting", False):
    filtered = [t for t in filtered if live_impeded(t)]
```

The recount that produces `hidden_drafts` replays only the first stage:

```python
hidden_drafts = 0
if not filtered and status != "all":
    hidden_drafts = len([
        t for t in filter_cards(cards, status=status, ..., include_drafts=True)
        if card_is_draft(t)
    ])
```

So it answers *"what would `filter_cards` have matched with drafts included?"*
rather than *"what would this query have matched?"* — and the answer is emitted
as an instruction:

```python
f"{hidden_drafts} {noun} hidden — author, then `goc publish <title>`"
```

There is a second, independent half. Even replaying `live_impeded` would not
fix `--waiting`, because `live_impeded` refuses drafts on its own axis
(`engine.py:2585-2589`):

```python
return (
    card.status not in TERMINAL_STATUSES
    and not card_is_draft(card)
    and waiting_impedes(card, today=today)
)
```

That is the **third** site the draft conjunct is inlined on. The predecessor
threaded `include_drafts` through the two it knew about — `filter_cards`
(`engine.py:2809`) and `card_is_ready` (`engine.py:2485`), whose docstring says
it exists so the reporting path can ask *"what would `--ready` have matched if
drafts counted as authored?"* — and stopped there. Without the same keyword on
`live_impeded`, that counterfactual is unanswerable under `--waiting`: the
helper short-circuits on the draft flag before it ever reads the overlay.

The predecessor's own DoD states the invariant this violates:

```
- [x] TDD: ... a genuinely empty deck (and a deck whose visible cards were
      dropped by a user filter) gains NO draft clause — the message must not
      grow a always-on conjunct
```

`--waiting` and `--closed-since` are exactly "a user filter" — they are just
the two that run outside `filter_cards`, so the guard that pins that invariant
never sees them.

## Empirical evidence

`uv run python .game-of-cards/deck/zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface/reproduce.py`:

```
A. goc --waiting --status open   (draft has NO waiting_on/waiting_until)
   No cards match (status: open; waiting: active impediment overlay; 1 unauthored draft scaffold hidden — author, then `goc publish <title>`).
   claims a draft is hidden : True
   publishing it would show it: False  (live_impeded needs an overlay)

B. goc --closed-since 1h --status done   (draft closed 2026-01-02)
   No cards match (status: done; closed-since: 1h; 1 unauthored draft scaffold hidden — author, then `goc publish <title>`).
   claims a draft is hidden : True
   publishing it would show it: False  (closed far outside the window)

C. control — goc --waiting --status open, draft IS impeded (waiting_on: external)
   No cards match (status: open; waiting: active impediment overlay; 1 unauthored draft scaffold hidden — author, then `goc publish <title>`).
   claims a draft is hidden : True
   publishing it would show it: True   (clause is correct here)

FAIL: deck(s) A, B report hidden drafts that publishing would not surface — the recount replays filter_cards only, skipping the --closed-since and --waiting conjuncts applied after it.
```

Decks A and C print **byte-identical** sentences while describing opposite
situations — the same collapse the predecessor card removed for the drained
deck, reintroduced one flag over.

## Reachability

Both shapes are ordinary two-flag queries, not malformed input:

- **A** needs `--waiting` with an explicit `--status`. Bare `goc --waiting`
  auto-extends `status` to `"all"` (`engine.py:3967-3975`), and the recount is
  skipped when `status == "all"`, so the defect hides behind the default and
  appears only once a reader narrows the query — `goc --waiting --status open`
  is the natural "what is impeding my open work?" question.
- **B** needs `--closed-since` with an explicit `--status done`, the same
  narrowing applied to the standup/retrospective read.

The draft cards involved need no unusual authoring: A is any held draft (this
repo has one — `escalate-repeatedly-auto-released-cards-without-an-attempt-counter`),
and B is any card closed while its `draft` flag was still set.

## Why it matters

The count *is* the fix the predecessor shipped — its commit message is explicit
that "an unconditional 'excludes drafts' note would still render identically on
an empty deck", so the clause earns its place only by being accurate. A wrong
count is worse than no clause: it sends the reader to author and publish a card
in order to reveal something that will still not appear, and the second
`goc publish` teaches that the message lies.

It also re-splits the read surfaces the predecessor reconciled. `goc --status all`
lists the card, the board marks it `✎`, and the table path now asserts a causal
claim about the draft flag that neither sibling supports.

Related, not duplicate:

- [empty-queue-line-reports-a-drained-deck-right-after-goc-new-scaffolds-a-card](../empty-queue-line-reports-a-drained-deck-right-after-goc-new-scaffolds-a-card/)
  — the predecessor that introduced `hidden_drafts`; closed, and this is the
  gap left where its `include_drafts` thread stopped.
- [query-flag-validation-is-opt-in-per-flag-and-new-flags-keep-missing-it](../query-flag-validation-is-opt-in-per-flag-and-new-flags-keep-missing-it/)
  — the umbrella this card advances, whose summary already names
  `--closed-since` composing with `--waiting` and with a non-terminal
  `--status` as unguarded compositions.
- [draft-gating-is-opt-in-per-surface-and-new-verbs-keep-missing-it](../draft-gating-is-opt-in-per-surface-and-new-verbs-keep-missing-it/)
  — the *other* draft family: surfaces that forget to exclude drafts. This card
  is the mirror image (a surface that over-attributes exclusion to the draft
  flag), but it shares that family's root observation — the draft conjunct is
  inlined per site, which is why `live_impeded` cannot answer the
  counterfactual. No edge: fixing this does not decide that card's
  default-inversion question.
- [waiting-impedes-callers-reimplement-the-terminal-status-liveness-gate-and-drift](../waiting-impedes-callers-reimplement-the-terminal-status-liveness-gate-and-drift/)
  — why `live_impeded` exists as the shared gate at all.

## Fix

Two changes, both continuing the pattern the predecessor established rather
than introducing a new one.

1. **Replay the whole query, not its first stage.** Factor the two
   post-`filter_cards` conjuncts in `_cmd_default` (`engine.py:4000-4016`) into
   one local narrowing step, and apply it to the recount as well as to
   `filtered`. This is the half that fixes `--closed-since`, which has no draft
   axis at all — it is simply a filter the recount forgot.

2. **Thread `include_drafts` through `live_impeded`** (`engine.py:2570`), the
   third site the draft conjunct is inlined on, exactly as
   `card_is_ready` (`engine.py:2457`) already carries it and for the same
   stated reason. Default unchanged, so every production read surface keeps
   excluding drafts; only the counterfactual recount passes it.

With both, the recount asks the question the clause claims to answer — *would
this card appear in this query if its draft flag were cleared?* — so deck C
keeps its clause and decks A and B lose theirs.

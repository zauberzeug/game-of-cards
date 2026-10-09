---
title: engine-comments-claim-unflagged-placeholder-cards-count-as-drafts
summary: "Three goc/engine.py comments said card_is_draft also catches a card that still carries both goc new placeholders but no draft flag, and a test docstring and a closed card's reproduce.py repeated the claim. card_is_draft keys on the flag alone by recorded design, so such a card is listed, pullable and supersedable like any other. The comments now say so, is_placeholder_scaffold names goc publish as its one consumer, and a twin-card regression test pins the flag-only contract on every draft-gated surface."
status: done
stage: null
contribution: low
created: "2026-10-08T05:40:20Z"
closed_at: "2026-10-09T04:43:04Z"
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [x] TDD: reproduce.py exits 0, so no comment in `goc/engine.py`, `tests/test_empty_query_result_line.py` or the closed zero-match card's `reproduce.py` claims the draft gate catches an unflagged placeholder scaffold, while `card_is_draft` still reads the flag alone
  - [x] TDD: a regression test pins the flag-only contract on an unflagged placeholder scaffold, which is not a draft (`card_is_draft` false, `draft: false` in `--json`, no `✎` in the table or on the board), is listed by `goc` and `goc --ready`, and gets the not-a-draft note from `goc publish`
  - [x] MECHANICAL: the corrected `is_placeholder_scaffold` docstring names `goc publish` as its only consumer, and the closed zero-match card's `log.md` carries a forward pointer to this card
worker: {who: "claude[bot]", where: main}
---

# Engine comments claim unflagged placeholder cards count as drafts

An "unflagged placeholder scaffold" is a card that still carries both
`goc new` placeholders, the stub DoD and the stub body, but no
`draft: true` flag. Two paths produce one: a card scaffolded before the
flag existed, or a scaffold whose flag was stripped by hand.

## Location

- `goc/engine.py:2764` (`is_placeholder_scaffold` docstring)
- `goc/engine.py:1010-1017` (`Card.draft` docstring)
- `goc/engine.py:3161` (`filter_cards` comment)
- `goc/engine.py:2780` (`card_is_draft` docstring, which was correct and
  is what the three above contradicted)
- `tests/test_empty_query_result_line.py:420-423` (a test docstring that
  copied the claim)
- `.game-of-cards/deck/zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface/reproduce.py:68`
  (a closed card's reproducer that copied the claim)
- `tests/test_unflagged_placeholder_scaffold_is_not_a_draft.py` (the
  regression test that pins the contract)

## What was broken

The code reads the flag and nothing else:

```python
def card_is_draft(card: Card) -> bool:
    ...
    Keyed on the flag ALONE, deliberately NOT on `is_placeholder_scaffold`: a
    card that is claimed (`active`) or closed before its body is filled in has
    already cleared the flag, and its claim/closure MUST stay visible and
    committable — a lingering placeholder body must not silently re-hide it.
    ...
    return card.draft
```

Three comments in the same file said the opposite:

```python
def is_placeholder_scaffold(card: Card) -> bool:
    """True iff the card still carries BOTH generated scaffold placeholders — the
    `goc new` DoD stub AND body stub. The flagless backstop in `card_is_draft`:
    catches legacy / hand-made scaffolds authored before the `draft` flag, and
    scaffolds whose flag was hand-stripped without authoring."""
```

```python
    def draft(self) -> bool:
        """... See `card_is_draft` for the composite
        predicate that also catches flagless legacy scaffolds."""
```

```python
    # Unauthored scaffolds (draft flag or surviving placeholder) are hidden from
    # every listing except `--status all`: ...
```

All four texts landed in one commit, `e861360e`, which introduced the
draft flag. The commit message settles which one is the design: "card_is_draft
keys on the flag alone, deliberately not on a lingering placeholder
body". So does the maintainer decision recorded on
[placeholder-cards-superseded-before-they-are-authored](../placeholder-cards-superseded-before-they-are-authored/):
"B's authored/draft flag becomes the shared basis A and C key off (more
robust than matching placeholder strings)". The three comments described
an earlier iteration of that same commit.

`is_placeholder_scaffold` has exactly one caller, `_cmd_publish`. It
consults the predicate only after `card_is_draft` has already returned
true, so the unflagged card is never checked against it at all.

## Empirical evidence

`uv run python .game-of-cards/deck/engine-comments-claim-unflagged-placeholder-cards-count-as-drafts/reproduce.py`
builds the card with `goc new` and strips the flag, then asks the real
CLI how it is treated. Before the fix:

```
=== comments claiming the draft gate catches unflagged placeholder scaffolds ===
  goc/engine.py: 'flagless backstop in `card_is_draft`'
  goc/engine.py: 'also catches flagless legacy scaffolds'
  goc/engine.py: 'draft flag or surviving placeholder'
  tests/test_empty_query_result_line.py: 'placeholder half of that predicate'
  .game-of-cards/deck/zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface/reproduce.py: '`card_is_draft` also fires on a surviving placeholder'

=== how goc treats an unflagged placeholder scaffold ===
  both placeholders present: True
  card_is_draft: False
  --json draft field: False
  listed by `goc`: True
  listed by `goc --ready`: True
  `goc publish` output: legacy-scaffold: not a draft; nothing to publish
  `goc status superseded` refused: False

=== verdict ===
DEFECT: 5 claim(s) say the draft gate catches the card, but card_is_draft returns False: it is listed, pullable and supersedable like authored work
exit=1
```

After the fix, the behavior block is unchanged, as intended, and the
claims are gone:

```
=== comments claiming the draft gate catches unflagged placeholder scaffolds ===
  (none)
...
=== verdict ===
OK: the comments and card_is_draft agree on unflagged placeholder scaffolds
exit=0
```

The script fails whenever the comments and `card_is_draft` disagree, in
either direction. It also passes if a backstop is built later and the
claims become true.

## Why it matters

The comments were already being believed. Two later artifacts restated
the false claim as the reason for their own setup. A regression test's
docstring said its cards were authored "so `card_is_draft` fires on the
explicit flag alone — the placeholder half of that predicate would
confound what is being measured here". A closed card's reproducer said
its cards were authored because "`card_is_draft` also fires on a
surviving placeholder scaffold". Both cards worked by accident, because
they authored their cards anyway.

The next reader might not have been so lucky. Someone who trusted the
`is_placeholder_scaffold` docstring would conclude that an old
unflagged scaffold is hidden from the queue and protected from
`goc status ... superseded`. It is neither. That is the exact race the
draft flag was built to close: an unauthored card superseded as a
"duplicate" on its title alone.

## Fix applied

The comments were corrected, not the code. The flag-only rule is a
recorded decision, and nothing here reopens it.

- `is_placeholder_scaffold`: the docstring names `goc publish`
  (`_cmd_publish`) as its one consumer, asked only about a card
  `card_is_draft` has already flagged. It points to `card_is_draft` for
  why the gate does not read the placeholders, and says an unflagged
  placeholder scaffold is ordinary queue work: listed, pullable and
  supersedable.
- `Card.draft`: "also catches flagless legacy scaffolds" is gone. The
  docstring now says `card_is_draft` reads the flag and nothing else.
- `filter_cards`: "or surviving placeholder" is gone, and so is "the
  board path renders the full deck", which stopped being true when the
  board began rendering the filtered set under an explicit `--status` or
  `--worker`. The true part stays: the board marks the drafts it shows.
- `tests/test_empty_query_result_line.py` and the closed card's
  `reproduce.py`: each now says its cards are authored so that each
  draft is one `goc publish` would actually release, and that the flag
  alone makes a card a draft. The closed card's `log.md` carries a
  forward pointer here.
- `tests/test_unflagged_placeholder_scaffold_is_not_a_draft.py` (8
  tests) builds two `goc new` twins and strips the flag from one, so the
  flag is the only difference between them. The flagged twin is the
  control on every surface. The unflagged twin is not a draft
  (`card_is_draft`, and `draft` / `ready` in `--json`), has no `✎` in
  the table or on the board, is listed by `goc` and `goc --ready`, gets
  the not-a-draft note from `goc publish` with its file untouched, and
  can be superseded. Two injected backstops show the test tells the
  contract apart from its violation. Making `card_is_draft` return
  `card.draft or is_placeholder_scaffold(card)` fails 7 of the 8 tests
  (all but the twins' precondition check). Adding a placeholder check
  to the supersede guard alone fails the supersede test.

Out of scope: whether unflagged placeholder scaffolds should be
protected after all. That would be a new decision against the recorded
one. If someone raises it, it belongs on its own card at
`human_gate: decision`.

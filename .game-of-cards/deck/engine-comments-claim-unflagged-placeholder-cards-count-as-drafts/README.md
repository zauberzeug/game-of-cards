---
title: engine-comments-claim-unflagged-placeholder-cards-count-as-drafts
summary: "Three goc/engine.py comments say card_is_draft also catches a card that still carries both goc new placeholders but no draft flag. card_is_draft keys on the flag alone, deliberately, as its own docstring and the maintainer decision on placeholder-cards-superseded-before-they-are-authored record, so such a card is listed, pullable and supersedable like any other. The false claim has already been copied into a test docstring and a closed card's reproduce.py."
status: active
stage: null
contribution: low
created: "2026-10-08T05:40:20Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [ ] TDD: reproduce.py exits 0, so no comment in `goc/engine.py`, `tests/test_empty_query_result_line.py` or the closed zero-match card's `reproduce.py` claims the draft gate catches an unflagged placeholder scaffold, while `card_is_draft` still reads the flag alone
  - [ ] TDD: a regression test pins the flag-only contract on an unflagged placeholder scaffold, which is not a draft (`card_is_draft` false, `draft: false` in `--json`, no `✎` in the table or on the board), is listed by `goc` and `goc --ready`, and gets the not-a-draft note from `goc publish`
  - [ ] MECHANICAL: the corrected `is_placeholder_scaffold` docstring names `goc publish` as its only consumer, and the closed zero-match card's `log.md` carries a forward pointer to this card
worker: {who: "claude[bot]", where: main}
---

# Engine comments claim unflagged placeholder cards count as drafts

An "unflagged placeholder scaffold" is a card that still carries both
`goc new` placeholders, the stub DoD and the stub body, but no
`draft: true` flag. Two paths produce one: a card scaffolded before the
flag existed, or a scaffold whose flag was stripped by hand.

## Location

- `goc/engine.py:2766` (`is_placeholder_scaffold` docstring)
- `goc/engine.py:1017` (`Card.draft` docstring)
- `goc/engine.py:3155` (`filter_cards` comment)
- `goc/engine.py:2784` (`card_is_draft` docstring, which is correct and
  is what the three above contradict)
- `tests/test_empty_query_result_line.py:421-422` (a test docstring that
  copied the claim)
- `.game-of-cards/deck/zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface/reproduce.py:68`
  (a closed card's reproducer that copied the claim)

## What's broken

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

Three comments in the same file say the opposite:

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
robust than matching placeholder strings)". The three comments describe
an earlier iteration of that same commit.

`is_placeholder_scaffold` has exactly one caller, `_cmd_publish`. It
consults the predicate only after `card_is_draft` has already returned
true, so the unflagged card is never checked against it at all.

## Empirical evidence

`uv run python .game-of-cards/deck/engine-comments-claim-unflagged-placeholder-cards-count-as-drafts/reproduce.py`
builds the card with `goc new` and strips the flag, then asks the real
CLI how it is treated:

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

The script fails whenever the comments and `card_is_draft` disagree, in
either direction. It passes if the claims go, and it would also pass if
a backstop were built and the claims became true.

## Why it matters

The comments are already being believed. Two later artifacts restate
the false claim as the reason for their own setup. A regression test's
docstring says its cards are authored "so `card_is_draft` fires on the
explicit flag alone — the placeholder half of that predicate would
confound what is being measured here". A closed card's reproducer says
its cards are authored because "`card_is_draft` also fires on a
surviving placeholder scaffold". Both cards worked by accident, because
they authored their cards anyway.

The next reader may not be so lucky. Someone who trusts the
`is_placeholder_scaffold` docstring would conclude that an old
unflagged scaffold is hidden from the queue and protected from
`goc status ... superseded`. It is neither. That is the exact race the
draft flag was built to close: an unauthored card superseded as a
"duplicate" on its title alone.

## Fix

The fix is to correct the comments, not the code. The flag-only rule is
a recorded decision, and nothing here reopens it.

- `is_placeholder_scaffold`: say what it is for. Its only consumer is
  `goc publish`, which refuses to release a draft that is still a pure
  placeholder. Point to `card_is_draft` for why the gate does not read
  it, and say that an unflagged placeholder scaffold is ordinary queue
  work.
- `Card.draft`: drop "also catches flagless legacy scaffolds".
- `filter_cards`: drop "or surviving placeholder". Also drop "the board
  path renders the full deck": since the board-worker-filter fix, the
  board renders the filtered set under an explicit `--status` or
  `--worker`. Keep the true part, that the board marks the drafts it
  shows.
- `tests/test_empty_query_result_line.py:421-422` and the closed card's
  `reproduce.py:68`: restate why the cards are authored without the
  claim. Add a forward pointer to this card in the closed card's
  `log.md`.

Out of scope: whether unflagged placeholder scaffolds should be
protected after all. That would be a new decision against the recorded
one. If someone raises it, it belongs on its own card at
`human_gate: decision`.

---
title: count-banners-outside-the-cards-sweep-print-1-boxes-instead-of-1-box
summary: "Nine count interpolations across seven sites in goc/engine.py hardcode a plural noun, so `goc done` on a card with one open box prints 'ERROR: <title>: 1 unchecked DoD boxes'. The closed cards sweep could not reach them: its scan required the bare word `cards` immediately after the interpolation, which misses every non-card noun (boxes, titles, summaries, items, lines) and also misses `{len(cluster)} blocked cards` — and the CI guard it installed inherits the same blind spot."
status: active
stage: null
contribution: low
created: "2026-07-27T01:30:21Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, meta-fix]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — no count interpolation in `goc/engine.py` is followed by a hardcoded plural noun, and `goc done` on a card with exactly one open box prints `1 unchecked DoD box`.
  - [ ] TDD: the CI guard in `tests/test_count_message_pluralization.py` is widened to catch BOTH classes the `cards` sweep missed — a non-card noun, and an adjective between the count and the noun (`{len(cluster)} blocked cards`) — and is proven by falsification: reintroduce one site of each class and confirm the test fails and names it.
  - [ ] MECHANICAL: all nine interpolations route through one shared pluralization definition. `_cards_noun()` is card-specific; decide whether to generalize it (and update its eight existing call sites) or add one general helper beside it, then apply that choice uniformly — do not leave two overlapping helpers.
  - [ ] PROCESS: `uv run goc validate` passes and `uv run python -m unittest discover -s tests` is green; the closed sibling card's forward pointer is accurate.
worker: {who: "claude[bot]", where: main}
---

# Count banners outside the cards sweep print "1 boxes" instead of "1 box"

## Location

Nine count interpolations at seven sites in `goc/engine.py`:

| Line | Banner | Noun class |
|---|---|---|
| 4293 | `ERROR: {title}: {t.dod_open} unchecked DoD boxes; will not mark done` | non-card |
| 4375 | `ERROR: {title}: {t.dod_open} unchecked DoD boxes; refusing bundled close` | non-card |
| 1723 | `{t.title}: definition_of_done: status=done with {t.dod_open} unchecked boxes` | non-card |
| 5036 | `{card.dod_open} unchecked boxes` (attest DoD check) | non-card |
| 4255 | `Applied: {n} titles, {n} summaries, {n} DoD items.` | non-card ×3 |
| 6214 | `> … +{len(preview_lines) - 6} more lines` | non-card |
| 2240 | `{len(cluster)} blocked cards rooted here (gate={root.human_gate})` | **card, with an adjective** |

`4293` is the most-read of them: it is the message `goc done` prints every time
a card is closed too early, so every agent and human who has ever tripped the
DoD gate on a one-box card has read `1 unchecked DoD boxes`.

## What's broken

Two structural gaps, not seven independent typos.

**Gap 1 — the helper is card-specific.** The sibling card
[deck-count-messages-print-1-cards-instead-of-1-card](../deck-count-messages-print-1-cards-instead-of-1-card/)
installed `goc/engine.py:1200`:

```python
def _cards_noun(count: int) -> str:
    return "card" if count == 1 else "cards"
```

Nothing in the module pluralizes `box`, `title`, `summary`, `item`, or `line`,
so those banners had no convention to adopt even in principle.

**Gap 2 — the sweep's own scan could not see past an adjective.** That card
defined its fix set with `\{len\([^)}]*\)\}\s+cards?\b` — the noun had to be the
bare word `cards`, directly after the interpolation. `goc/engine.py:2240` is a
*card* banner:

```python
    f"{len(cluster)} blocked cards rooted here (gate={root.human_gate})",
```

The word `blocked` sits between the count and the noun, so the sweep's regex
never matched it. It is a `cards` site that a card-noun sweep declared complete.

The consequence is that the CI guard the sweep installed
(`tests/test_count_message_pluralization.py`) inherits the identical blind spot —
its pattern is `\{len\([^)}]*\)\}\s+cards?\b(?!\(s\))`. The guard reports the
convention as enforced while nine interpolations, one of them a `cards` banner,
sit outside its reach. That is the part worth fixing carefully: a guard that
under-reports is worse than no guard, because it converts an open defect into a
claim of completeness.

## Empirical evidence

```
$ uv run python .game-of-cards/deck/count-banners-outside-the-cards-sweep-print-1-boxes-instead-of-1-box/reproduce.py
static scan — count banners followed by a hardcoded plural noun:
  goc/engine.py:1723  [unchecked boxes]  errors.append(f"{t.title}: definition_of_done: status=done with {t.dod_open} unchecked boxes
  goc/engine.py:2240  [blocked cards]  f"{len(cluster)} blocked cards rooted here (gate={root.human_gate})",
  goc/engine.py:4255  [titles]  f"Applied: {applied_count['title']} titles, {applied_count['summary']} summaries, {applied_c
  goc/engine.py:4255  [summaries]  f"Applied: {applied_count['title']} titles, {applied_count['summary']} summaries, {applied_c
  goc/engine.py:4255  [DoD items]  f"Applied: {applied_count['title']} titles, {applied_count['summary']} summaries, {applied_c
  goc/engine.py:4293  [unchecked DoD boxes]  print(f"ERROR: {title}: {t.dod_open} unchecked DoD boxes; will not mark done", file=sys.stde
  goc/engine.py:4375  [unchecked DoD boxes]  f"ERROR: {title}: {t.dod_open} unchecked DoD boxes; refusing bundled close",
  goc/engine.py:5036  [unchecked boxes]  return False, f"{card.dod_open} unchecked boxes"
  goc/engine.py:6214  [more lines]  f"  > … +{len(preview_lines) - 6} more lines "

  of those, card-noun banners the cards sweep's own regex never matched:
    goc/engine.py:2240  [blocked cards]

live — `goc done` on a card with exactly one unchecked box:
  ERROR: one-open-box: 1 unchecked DoD boxes; will not mark done

FAIL: 9 count banner(s) hardcode a plural noun — 1 of them are card banners the `cards` sweep's regex never matched, and its CI guard inherits the same blind spot
```

The static scan uses an explicit countable-noun vocabulary rather than a bare
`\w+s` pattern — the loose form matches verbs (`has`, `contains`, `differs`) and
produced 37 false positives on the first attempt.

## Why it matters

`4293` is the DoD gate's refusal message — the single most-read error string in
the tool, and the one a new user meets first. The `cards` sweep was filed
because "seven sites is past the threshold where fixing one in passing just
leaves six behind"; it then left nine behind, including a more visible one than
any it fixed.

The reachability is trivial for every site: any card with exactly one open DoD
box hits `4293`, `1723`, and `5036`; a single applied rewrite hits `4255`; a
seven-line decision preview hits `6214`; a one-card blocked cluster hits `2240`.

## Fix

Route all nine interpolations through one shared pluralization definition, then
widen the CI guard to cover both classes that leaked.

The helper question is a real choice and the DoD leaves it open deliberately:

- **Generalize** `_cards_noun(count)` into something like
  `_plural(count, singular, plural=None)` and update its eight existing call
  sites. One definition for every noun; costs churn on code that landed in the
  sibling card's commit.
- **Add** a general helper beside `_cards_noun`. Smaller diff; leaves two
  overlapping helpers, which is the "do not introduce a third form" smell the
  sibling card explicitly warned against.

Either is defensible — but the guard work is not optional in either case. The
guard must reject a count interpolation followed by an *optional adjective run*
and then any countable noun, or the next sweep inherits the same hole a third
time.

Do not simply reword the banners to dodge plurals (`boxes: 1`): `4293` and
`4375` are error messages, and prose banners are what the sibling card chose the
grammatical form for.

**One existing test will break, by design.**
`tests/test_done_bundle.py:77` (`test_bundle_refuses_unchecked_dod`) builds its
fixture with `dod_open=1` and then asserts:

```python
            self.assertIn("unchecked DoD boxes", result.stderr)
```

Fixing site `4375` makes that stderr read `1 unchecked DoD box`, so the
assertion fails on the plural substring. Update it to the singular — the failure
is the fix working, not a regression. Two nearby assertions are safe either way:
`tests/test_close_terminal_gate_guard.py:215` and `:250` use
`assertNotIn("unchecked DoD boxes", ...)` to check the message is absent
entirely, which a singular form also satisfies. No other test in the suite
matches on this wording.

## Relationship to the closed sibling

This is not a duplicate of
[deck-count-messages-print-1-cards-instead-of-1-card](../deck-count-messages-print-1-cards-instead-of-1-card/)
and not a generalization umbrella over it. That card's scope — the bare-`cards`
noun — is genuinely closed and its seven sites are genuinely fixed. This card
covers the two classes its scan could not express, and repairs the guard it
installed. The closed card carries a forward pointer to here, per "closure is
not frozenness".

---
title: count-banners-outside-the-cards-sweep-print-1-boxes-instead-of-1-box
summary: "Nine count interpolations across seven sites in goc/engine.py hardcode a plural noun, so `goc done` on a card with one open box prints 'ERROR: <title>: 1 unchecked DoD boxes'. The closed cards sweep could not reach them: its scan required the bare word `cards` immediately after the interpolation, which misses every non-card noun (boxes, titles, summaries, items, lines) and also misses `{len(cluster)} blocked cards` — and the CI guard it installed inherits the same blind spot."
status: done
stage: null
contribution: low
created: "2026-07-27T01:30:21Z"
closed_at: "2026-07-27T01:49:22Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, meta-fix]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — no count interpolation in `goc/engine.py` is followed by a hardcoded plural noun, and `goc done` on a card with exactly one open box prints `1 unchecked DoD box`.
  - [x] TDD: the CI guard in `tests/test_count_message_pluralization.py` is widened to catch BOTH classes the `cards` sweep missed — a non-card noun, and an adjective between the count and the noun (`{len(cluster)} blocked cards`) — and is proven by falsification: reintroduce one site of each class and confirm the test fails and names it.
  - [x] MECHANICAL: all nine interpolations route through one shared pluralization definition. `_cards_noun()` is card-specific; decide whether to generalize it (and update its eight existing call sites) or add one general helper beside it, then apply that choice uniformly — do not leave two overlapping helpers.
  - [x] MECHANICAL (added at closure): the prose that documents a fixed banner is fixed with it — `goc/templates/skills/finish-card/SKILL.md` quoted `<n> unchecked DoD boxes`, which the fix made wrong for `<n>` = 1. Not implied by the four criteria above, but leaving it would reproduce this card's own defect one layer out, in the doc rather than the code.
  - [x] PROCESS: `uv run goc validate` passes and `uv run python -m unittest discover -s tests` is green; the closed sibling card's forward pointer is accurate.
worker: {who: "claude[bot]", where: main}
---

# Count banners outside the cards sweep print "1 boxes" instead of "1 box"

## Location

Nine count interpolations at seven sites in `goc/engine.py`. Line numbers are
the pre-fix ones; several banners became multi-line when the helper call was
threaded in, so they have shifted since:

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

Before the fix, `reproduce.py` named all nine sites and exited 1:

```
static scan — count banners followed by a hardcoded plural noun:
  goc/engine.py:1723  [unchecked boxes]      definition_of_done: status=done with {t.dod_open} unchecked boxes
  goc/engine.py:2240  [blocked cards]        f"{len(cluster)} blocked cards rooted here (gate={root.human_gate})",
  goc/engine.py:4255  [titles]               f"Applied: {applied_count['title']} titles, …
  goc/engine.py:4255  [summaries]            … {applied_count['summary']} summaries, …
  goc/engine.py:4255  [DoD items]            … {applied_count['dod']} DoD items."
  goc/engine.py:4293  [unchecked DoD boxes]  {t.dod_open} unchecked DoD boxes; will not mark done
  goc/engine.py:4375  [unchecked DoD boxes]  {t.dod_open} unchecked DoD boxes; refusing bundled close
  goc/engine.py:5036  [unchecked boxes]      return False, f"{card.dod_open} unchecked boxes"
  goc/engine.py:6214  [more lines]           f"  > … +{len(preview_lines) - 6} more lines "

  of those, card-noun banners the cards sweep's own regex never matched:
    goc/engine.py:2240  [blocked cards]

live — `goc done` on a card with exactly one unchecked box:
  ERROR: one-open-box: 1 unchecked DoD boxes; will not mark done

FAIL: 9 count banner(s) hardcode a plural noun — 1 of them are card banners the `cards` sweep's regex never matched, and its CI guard inherits the same blind spot
```

After, the same script exits 0:

```
static scan — count banners followed by a hardcoded plural noun:
  (none)

  of those, card-noun banners the cards sweep's own regex never matched:
    (none)

live — `goc done` on a card with exactly one unchecked box:
  ERROR: one-open-box: 1 unchecked DoD box; will not mark done

PASS: every count banner in goc/engine.py pluralizes correctly
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

## Fix (applied)

**Helper: generalized, not duplicated.** `_cards_noun(count)` is gone;
`goc/engine.py:1200` now defines

```python
def _plural(count: int, singular: str, plural: str | None = None) -> str:
```

with `plural` defaulting to `singular + "s"` and passed explicitly for nouns
that need it (`box` → `boxes`, `summary` → `summaries`). The eight existing
call sites read `_plural(…, "card")`; the nine that had no helper to route
through now route through this one. One definition for every noun — the
alternative (a general helper *beside* `_cards_noun`) was rejected because it
leaves two overlapping helpers, the smell the sibling card warned against.
The banners keep their prose form; none was reworded to dodge the plural.

**Guard: widened on two axes and proven by falsification.**
`tests/test_count_message_pluralization.py` now matches any interpolation
(`\{[^{}]+\}`, not just `\{len\(…\)\}`), then an optional run of up to two
adjective words, then a noun from an explicit countable-noun vocabulary. It
also splices implicitly-concatenated f-string fragments before scanning, so a
count and its noun split across two source lines cannot hide — the same shape
of blind spot one level down. `GuardCatchesBothMissedClassesTest` pins that
reach permanently by running the scanner over synthetic source carrying one
offender of each class and asserting it is named. Beyond that, the guard was
falsified against the real engine: reintroducing `4293` (non-card noun) and
`2240` (adjective between count and noun) turned it red and it named both
sites by line and phrase; the revert was then undone.

**Two more surfaces the fix reached.**

- `tests/test_done_bundle.py` (`test_bundle_refuses_unchecked_dod`) built its
  fixture with `dod_open=1` and asserted the plural substring, so it broke by
  design; it now asserts the exact singular refusal and rejects the plural.
  `tests/test_close_terminal_gate_guard.py:215` and `:250` were safe either
  way — they use `assertNotIn` to check the message is absent entirely.
- `goc/templates/skills/finish-card/SKILL.md` documented the refusal as
  `<n> unchecked DoD boxes`. With `<n>` a placeholder that can be 1, the fix
  made that doc line wrong, so it reads `box(es)` now. The plugin mirrors and
  the OpenClaw port were regenerated from the template.

`tests/test_triage_decision_preview_overflow.py` already covered site `6214`
only in the plural (its fixture hides 2 lines); a 7-line fixture asserting
`… +1 more line` was added.

## Relationship to the closed sibling

This is not a duplicate of
[deck-count-messages-print-1-cards-instead-of-1-card](../deck-count-messages-print-1-cards-instead-of-1-card/)
and not a generalization umbrella over it. That card's scope — the bare-`cards`
noun — is genuinely closed and its seven sites are genuinely fixed. This card
covers the two classes its scan could not express, and repairs the guard it
installed. The closed card carries a forward pointer to here, per "closure is
not frozenness".

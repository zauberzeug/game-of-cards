---
title: citation-repair-pass-maps-range-endpoints-independently-and-corrupts-the-range
summary: "The refine-deck citation recipe rewrites a range cite's two endpoints as unrelated single-line lookups, so a repair pass can move the start past the end or stretch a 3-line span to 232. Twelve such cites now sit in eight open cards, all written by the three anchored repair passes of 2026-08; each addresses no code block at all, which is the whole content of a range cite. The corruption is self-perpetuating and invisible: an incoherent range whose endpoints both still anchor cleanly verdicts as `current`, so the next pass never looks at it."
status: done
stage: null
contribution: medium
created: "2026-09-07T02:07:44Z"
closed_at: "2026-09-07T04:44:34Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — no card in the deck carries a range cite whose start is past its end or whose span exceeds a plausible block.
  - [x] MECHANICAL: the twelve cites `reproduce.py` names today are repaired by hand from each card's own prose (the recipe cannot recover them; both endpoints anchor cleanly at unrelated code).
  - [x] MECHANICAL: `goc/templates/skills/refine-deck/reference.md:157-186` states the coherence requirement — a range repair that would leave the endpoints unordered or implausibly far apart is a decline, reported like every other decline, not a rewrite. `SKILL.md:123-130` (step 1 of the per-cite recipe) reads consistently.
  - [x] MECHANICAL: the same section says an already-incoherent range is reported rather than re-mapped, so a pass stops laundering a corrupt cite into a differently corrupt one.
  - [x] TDD: a regression test feeds a synthetic drifted range to the rule as written and fails on today's text, proving the guard can catch an offender rather than passing on an empty list (see [static-source-guards-never-prove-they-can-catch-an-offender](../static-source-guards-never-prove-they-can-catch-an-offender/)).
  - [x] MECHANICAL: all five mirrors regenerate — `python scripts/sync_plugin_assets.py --check` and `python3 scripts/port_skills_to_openclaw.py --check` clean.
  - [x] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass.
worker: {who: "claude[bot]", where: main}
---

# Citation repair maps range endpoints independently and corrupts the range

## Location

- `goc/templates/skills/refine-deck/reference.md:157-186` — § "A range is
  one cite, not two" and § "Do not re-map a range that ARRIVES
  incoherent", the two rules that replaced the single sentence below.
- `goc/templates/skills/refine-deck/reference.md:228` — the fourth
  decline row, `incoherent range pair`.
- `goc/templates/skills/refine-deck/SKILL.md:123-130` — step 1 of the
  core recipe, carrying the same two rules in short form.
- `tests/test_refine_deck_citation_anchor.py` — the guard:
  `DocumentedRangeCoherenceTest` classifies the shipped prose,
  `RangeRepairTest` runs the recipe over a fixture that reproduces the
  endpoint divergence.

The rule this replaced read, from `50da03d1` (2026-08-10) to
`9d5bd88f` (2026-09-07):

```
A range (`file.py:120-140`) maps its endpoints independently and is
rewritten only when both resolve.
```

with `Ranges map both endpoints.` as its one-line form in the core
recipe. It shipped closing
[refine-deck-citation-check-cannot-detect-line-drift-in-a-growing-file](../refine-deck-citation-check-cannot-detect-line-drift-in-a-growing-file/).

## What was broken

"Maps its endpoints independently" is two single-line repairs that happen
to be written next to each other. Each endpoint gets its own anchor, its
own uniqueness test, its own relocation — and nothing afterwards asks
whether the pair still bounds a block. It usually does, because code above
a block moves both of its edges by the same amount. It stops doing so the
moment the two anchors drift by different amounts, and there is no
condition in the recipe under which that outcome is refused.

A range cite is not two line numbers. `file.py:120-140` asserts *this
block*, and the endpoints are how the block is addressed. The moment the
start passes the end, or a 3-line body becomes a 232-line one, the cite
has stopped naming anything — it is strictly worse than the drifted cite
it replaced, because a drifted `file.py:120` at least points somewhere a
reader can orient from.

### The corruption compounds across passes

One cite, traced through every pass that touched it. The card is
[goc-new-stamps-goc-worker-queue-filter-into-authored-worker-field](../goc-new-stamps-goc-worker-queue-filter-into-authored-worker-field/),
line 3 of its README:

| Pass | Cite | Span |
|---|---|---|
| `73a90123` 2026-06-03 (filed) | `engine.py:2830-2833` | 3 |
| `2f6e8829` 2026-06-21 hygiene | `engine.py:2830-2833` | 3 |
| `69e1e4f2` 2026-08-10 first anchored repair | `engine.py:3735-3738` | 3 |
| `f290f5f7` 2026-08-17 hygiene | `engine.py:3903-3738` | **inverted** |
| `e8449764` 2026-08-24 hygiene | `engine.py:3970-3738` | **inverted** |
| `9bad9881` 2026-08-31 hygiene | `engine.py:4020-3788` | **inverted** |

The 2026-08-10 pass mapped both endpoints by the same +905 and kept the
block. The 2026-08-17 pass moved the start by +168 and left the end where
it was, because the end's anchor text had not moved. From that point on
each pass re-mapped whichever endpoint had drifted and left the wreck
ordered backwards.

### And then it becomes invisible

Once both endpoints anchor cleanly at their own lines, the recipe's own
verdict for `engine.py:4020-3788` is `current`. It is not a decline the
pass reports; it is a cite the pass certifies. Today those two lines in
`goc/engine.py` hold:

```python
# goc/engine.py:4020
    return f"No cards match ({'; '.join(parts)})."
# goc/engine.py:3788
    p_qp.add_argument("--yes", dest="auto_yes", action="store_true",
```

A queue-message helper and a `quality-pass` argparse flag, in that order,
standing in for a 3-line block about `goc new`'s worker field. Nothing in
the deck reports this, and nothing will: the reported residue is built
from declines, and this cite never declines.

## Empirical evidence

`uv run python .game-of-cards/deck/citation-repair-pass-maps-range-endpoints-independently-and-corrupts-the-range/reproduce.py`

```
scanned 747 cards
incoherent range cites: 0

```

Exit code 0. The twelve cites the pre-fix run named are repaired — each
re-derived by hand from its own card's prose, because both of its
endpoints anchored cleanly at unrelated code and no mechanical recipe
could recover the block. The pre-fix census, and the per-cite before/after
table, are in `log.md`.

The scan skips this card's own README, which is the catalogue of the
corruption: its compounding trace and its pre-fix transcript are dated
records of numbers past commits emitted, which the recipe's own scope rule
already excludes from repair. Every other card is scanned.

## Why it matters

A card's `## Location` block is the one thing a cold reader uses to reach
the code the card is about, and eight open cards pointed at a block that
did not exist. Seven of them are `human_gate: decision`, so the reader who
eventually arrives is a human spending a decision slot, and the first
thing they would have found is a citation that cannot be followed.

The self-perpetuating half is what made this worth a fix rather than a
sweep. The 2026-09-07 pass added an ad-hoc coherence guard and it fired on
one *new* inversion it was about to write
(`scripts/sync_plugin_assets.py:270-272` → `274-272`) — so the rate was
roughly one fresh corruption per pass, against a residue no pass reported.
Left alone, the count only went up; that ad-hoc guard is now the shipped
rule.

This is the fourth per-shape gap found in the same recipe, after
[refine-deck-citation-check-cannot-detect-line-drift-in-a-growing-file](../refine-deck-citation-check-cannot-detect-line-drift-in-a-growing-file/)
(the bounds test could not fire),
[second-citation-repair-pass-moves-correct-cites-onto-unrelated-code](../second-citation-repair-pass-moves-correct-cites-onto-unrelated-code/)
(the anchor commit was wrong on a second pass), and
[citation-repair-pass-has-no-rule-for-cites-inside-fenced-code-blocks](../citation-repair-pass-has-no-rule-for-cites-inside-fenced-code-blocks/)
(labels versus records). Each was found by running the recipe and reading
what it produced, which is the only way any of them surfaced. The
convention-level question — whether a bare line number should address code
at all — is parked on
[file-line-citations-drift-again-within-days-of-every-repair-pass](../file-line-citations-drift-again-within-days-of-every-repair-pass/);
this card is the narrower one that holds whatever the convention becomes,
because a range still has to bound something.

## Fix

Two rules added to the recipe, both in the shape it already uses for the
uniqueness-and-substance guard — refuse to emit an output the pass cannot
justify, and report the refusal:

1. **Coherence check on the repaired pair.** After both endpoints resolve,
   accept the rewrite only if the pair is ordered (`start <= end`) and the
   new span still fits a block (over 500 lines is not a block). Otherwise
   decline, and report it in the residue table alongside trivial /
   ambiguous / absent — a fourth decline reason, not a silent skip.
2. **Do not re-map an already-incoherent range.** A cite that arrives with
   `start > end`, or with a span no block could have, is a corruption from
   an earlier pass, not drift. Its endpoints anchor to whatever they were
   last mistakenly moved onto, so re-mapping launders it. Report it for a
   human to re-derive from the card's prose.

The twelve existing cites got the hand repair; no mechanical recipe could
recover them, because each endpoint anchored cleanly to the unrelated line
it had been moved onto.

The guard is the prose classifier plus a fixture, in
`tests/test_refine_deck_citation_anchor.py` beside the two earlier
per-shape gaps in the same recipe. The fixture reproduces the exact
coincidence the deck census found: a block cited `6-8` whose line 8 holds
an idiom that also sits four lines above it, so inserting four lines above
the module moves the START anchor while the END anchor still reads
unchanged at its own number. Run without the pair check it writes `10-8`;
run with the shipped rule it declines. Both directions are asserted, and
the prose classifier is fed the sentence this replaced to prove it can
return the failing verdict rather than only the passing one.

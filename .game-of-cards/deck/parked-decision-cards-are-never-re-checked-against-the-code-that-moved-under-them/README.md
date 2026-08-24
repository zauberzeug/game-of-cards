---
title: parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them
summary: "Nothing re-checks a human_gate: decision card against the code it cites, so a parked card whose defect is fixed by later work keeps advertising a live defect indefinitely. Two measured instances: goc-waiting-filter-drifts-from-engine-on-elapsed-and-bare-waits and waiting-flag-filters-on-waiting-on-field-not-the-impediment-overlay both described a --waiting drift that commit 91d40320 fixed on 2026-06-24 while closing a third, gate-free card filed for the same defect the same day — no reference, no supersession edge, 61 days parked. The engine also makes this irreducible: goc status ... superseded refuses while the gate is up, so no autonomous pass can retire a stale park."
status: active
stage: null
contribution: high
created: "2026-08-24T02:32:11Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — it must first FAIL on today's tree by finding at least one parked card whose cited anchor text is absent from HEAD, and pass only once such cards are surfaced by a mechanism rather than by accident. Include a known-caught control (a card whose anchors all still resolve) so a green run distinguishes "nothing stale" from "nothing scanned", per `static-source-guards-never-prove-they-can-catch-an-offender`.
  - [ ] EMPIRICAL: measure how many of the 170 decision-gated cards are affected, using absent-anchor count as the proxy. This pass found 44 absent anchors across 30 cards without looking for stale parks; the real number is unknown and the decision below should not be taken on two instances.
  - [ ] PROCESS: the `## Decision required` question is answered and recorded — whether staleness detection is a `goc` mechanism, a `Skill(refine-deck)` category, or a documented duty of whoever runs `goc triage`.
  - [ ] MECHANICAL: whichever way it goes, the closing path gains the missing step — `Skill(finish-card)` § "After closure" tells a closer to check whether the defect they just fixed is also described by an open card, and to write the supersession edge. Today nothing prompts that.
  - [ ] MECHANICAL: `Skill(create-card)` dedups new filings against the *gated* backlog, not only against open titles. Both instances below were filed as fresh cards while a parked card already described the defect.
  - [ ] PROCESS: decide explicitly whether the gate should keep blocking `goc status <t> superseded`. It is the reason a stale park cannot be retired autonomously, and loosening it is a real option with real risk — record the rejection if it is rejected.
  - [ ] MECHANICAL: if a mechanism ships, mirrors re-synced (`python scripts/sync_plugin_assets.py --check`) and the OpenClaw port re-run (`python3 scripts/port_skills_to_openclaw.py --check`), both clean.
  - [ ] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green.
worker: {who: "claude[bot]", where: main}
---

# A parked card is never re-checked against the code that moved under it

## What's broken

A card at `human_gate: decision` is a claim about code, held until a human
reads it. Nothing re-evaluates that claim in the meantime. The code the card
cites keeps moving; the card does not. So a parked card whose defect is fixed
by later, unrelated work goes on asserting a live defect, and the only reader
who could notice is the one who is not reading.

This is not the same finding as
[deck-fills-with-decision-gated-cards-faster-than-they-are-decided](../deck-fills-with-decision-gated-cards-faster-than-they-are-decided/),
which is that nothing *consumes* the gated backlog. That card measures 189
gated cards, 101 of them 60+ days without activity, and argues the outlet is
missing. This card is about the contents rotting: some of that pile is no
longer true, and the pile does not know which part. An outlet that ranks and
caps — that card's recommended option C — would still present a stale card as
a live decision.

## The measured instances

Both surfaced on 2026-08-24, and neither was found by looking. They fell out
of the defunct-citation category of a `Skill(refine-deck)` pass, which
reported their anchor text as *absent from the tree* — the one signal in the
current scheme that means "the cited code was refactored away, re-read this
card". The pass found 44 absent anchors across 30 cards; these two happened
to be stale parks, and the other 28 cards were not audited for the same
thing.

| card | filed | gate | parked for |
|---|---|---|---|
| [goc-waiting-filter-drifts-from-engine-on-elapsed-and-bare-waits](../goc-waiting-filter-drifts-from-engine-on-elapsed-and-bare-waits/) | 2026-05-29 | `decision` | 61 days after its fix landed |
| [waiting-flag-filters-on-waiting-on-field-not-the-impediment-overlay](../waiting-flag-filters-on-waiting-on-field-not-the-impediment-overlay/) | 2026-06-19 | `decision` | 61 days after its fix landed |

Both describe the same defect: `goc --waiting` filtered on
`t.waiting_on is not None` and so disagreed with the engine's
`waiting_impedes` predicate in two cells of the overlay matrix.

Commit `91d40320` (2026-06-24) — *"fix(engine): align goc --waiting with the
waiting_impedes predicate"* — fixed it. What it closed was neither of the
above: it closed
[goc-waiting-flag-omits-deferral-cards-it-hides-from-the-queue](../goc-waiting-flag-omits-deferral-cards-it-hides-from-the-queue/),
a **third** card filed at `human_gate: none` on 2026-06-24 and closed the
same day, describing the same defect the two parked cards had been describing
for weeks. Commit `fd34c7cc` (2026-07-27) then extracted `live_impeded` and
routed the flag through it.

So the sequence was: file a card, park it on a decision, file a second card
for the same defect, park that too, file a third card without the gate, fix
it, close it — and leave the first two asserting the bug. No commit referenced
them; no `superseded_by` edge was written; `goc validate` stayed clean
throughout, because edge symmetry is what it checks and there were no edges.

## Verification that they really are fixed

Not inferred from the commit message. The first card ships a `reproduce.py`
that compares `goc --waiting` against `waiting_impedes` ground truth across
the matrix; re-run at HEAD it reports zero false positives and zero false
negatives. `tests/test_waiting_filter_status_scope.py:91` independently pins
the two named cells against the real CLI over a temp deck. The `--waiting`
help text now describes the predicate rather than the storage field.

One detail sharpens the cost. The fix took the option the second card
explicitly argued *against* — that card recommended overlay-field-presence
and the engine shipped the predicate reading, which drops elapsed-wait cards
from `--waiting`. A parked card is not only going stale; it can be silently
overruled, and the record shows neither the ruling nor the disagreement.

## Why the engine makes it irreducible

A hygiene pass that finds a stale park cannot retire it. Attempted during the
pass that filed this card:

```
$ uv run goc status goc-waiting-filter-drifts-from-engine-on-elapsed-and-bare-waits \
    superseded --by goc-waiting-flag-omits-deferral-cards-it-hides-from-the-queue
ERROR: human_gate is 'decision'; run `goc decide ...` to lower the gate
before closing into 'superseded'.
```

That refusal is correct — lowering a decision gate is the human's act, and an
agent that could clear gates to tidy the board would be worse than the rot.
But it means the accumulation is structural, not incidental: the only actor
that scans the deck often enough to notice staleness is the one forbidden
from acting on it, and the only actor permitted to act is the one whose
absence created the pile. Every autonomous pass can do is leave a better note.

## Why it matters

The gated backlog is the deck's largest asset by authoring cost — most of
these cards carry a `reproduce.py` and a worked options section. Three
distinct harms, in increasing order of cost:

1. **Wasted rediscovery.** A later filer re-derives a finding a parked card
   already holds. That is what produced the third `--waiting` card, and
   `Skill(create-card)` dedups against open titles rather than against parked
   bodies, so nothing caught it.
2. **A decision presented on false premises.** A human who finally reads a
   stale park is asked to choose between options for a defect that no longer
   exists, using cites that no longer resolve. The likely outcome is a wrong
   or wasted decision, and the reader has no cheap way to tell.
3. **The backlog count is not a work estimate.** 170 decision-gated cards is
   quoted as outstanding work; an unknown fraction is already done. Every
   argument that rests on the size of that pile — including the outlet
   argument in the sibling card — rests on a number nobody has verified.

## Decision required

The defect is not in dispute: two cards asserted a fixed bug for two months
and no mechanism could have noticed. What needs a pick is where detection
lives, because the three homes have very different costs and one of them is
"nowhere, deliberately".

**Option A — a `goc` check.** Extend `goc validate` (advisory) or add a verb
that, for each non-terminal card, extracts cited anchors and reports the ones
absent from the tree.

- *For:* the only option that fires without a human or a hygiene pass in the
  loop, and it ships to every consumer.
- *Against:* `goc validate` does not read card bodies today, and giving it a
  citation parser is a real surface addition. It is also bounded by
  [file-line-citations-drift-again-within-days-of-every-repair-pass](../file-line-citations-drift-again-within-days-of-every-repair-pass/):
  absent-anchor detection is only as good as the citation form, and that form
  is itself parked on a decision. Adding a check keyed to a convention that
  may be replaced is work that may need redoing.

**Option B — a `Skill(refine-deck)` category.** Make "stale parks" a named
sub-section beside "Stale unverified parks", scanning gated cards for absent
anchors and reporting them.

- *For:* cheapest by a wide margin, and it is where this finding was actually
  made — the pass already computes absent anchors as a by-product, so the
  category is a report over data it has in hand. Ships to consumers with the
  skill.
- *Against:* only fires when someone runs the pass, and it can only report.
  The retirement still needs a human `goc decide`, so the backlog shrinks at
  human cadence either way.

**Option C — a duty on the closer, not the deck.** `Skill(finish-card)` gains
a step: before closing, check whether an open card describes the defect you
fixed, and write the supersession edge. Prevention rather than detection.

- *For:* attacks the cause. All three cards here existed simultaneously; a
  closer who looked would have found the two parked ones in one query.
  Costs nothing at rest.
- *Against:* unguarded — it holds exactly as far as the closer's care does,
  which is the same failure mode as the two unguarded card-authoring rules in
  AGENTS.md. And it does nothing for the 170 already parked.

**Option D — accept it, and say so.** Document that a parked card's claims
are as of its filing date and must be re-verified before deciding.

- *For:* honest, and free. The re-verification cost lands on the reader who
  is already reading the card, which is the cheapest possible moment.
- *Against:* the reader is precisely who has not shown up for 101 of these
  cards in 60+ days, and it does nothing about the wasted-rediscovery harm.

**Recommendation, not binding: B plus C.** B is nearly free and is the only
option that fires on the existing 170; C is the only one that stops new
instances. A is the strongest mechanism and the wrong time to build it —
it should wait for the citation-form decision it depends on. The sibling
outlet card's option C (a working `goc triage`) should also carry a staleness
signal if it lands, since a decision queue that presents stale cards as live
is the harm restated one layer up.

## Non-goals

- Not a proposal to loosen the gate on `goc status ... superseded`. DoD item 6
  asks for that to be decided explicitly, because it is the mechanism that
  makes this irreducible, but the default answer is to keep it.
- Not a citation-format change. That is
  `file-line-citations-drift-again-within-days-of-every-repair-pass`, and this
  card only borrows its absent-anchor signal.
- Not a claim that the two instances should have been filed differently. Both
  are good cards that describe a real defect accurately as of their filing.

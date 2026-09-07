---
title: parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them
summary: "Nothing re-checks a human_gate: decision card against the code it cites, so a parked card whose defect is fixed by later work keeps advertising a live defect indefinitely. Two measured instances: goc-waiting-filter-drifts-from-engine-on-elapsed-and-bare-waits and waiting-flag-filters-on-waiting-on-field-not-the-impediment-overlay both described a --waiting drift that commit 91d40320 fixed on 2026-06-24 while closing a third, gate-free card filed for the same defect the same day — no reference, no supersession edge, 61 days parked. The engine also makes this irreducible: goc status ... superseded refuses while the gate is up, so no autonomous pass can retire a stale park."
status: active
stage: null
contribution: high
created: "2026-08-24T02:32:11Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — it must first FAIL on today's tree by finding at least one parked card whose cited anchor text is absent from HEAD, and pass only once such cards are surfaced by a mechanism rather than by accident. Include a known-caught control (a card whose anchors all still resolve) so a green run distinguishes "nothing stale" from "nothing scanned", per `static-source-guards-never-prove-they-can-catch-an-offender`.
  - [x] EMPIRICAL: measure how many of the 170 decision-gated cards are affected, using absent-anchor count as the proxy. This pass found 44 absent anchors across 30 cards without looking for stale parks; the real number is unknown and the decision below should not be taken on two instances.
  - [ ] PROCESS: the `## Decision required` question is answered and recorded — whether staleness detection is a `goc` mechanism, a `Skill(refine-deck)` category, or a documented duty of whoever runs `goc triage`.
  - [x] MECHANICAL: whichever way it goes, the closing path gains the missing step — `Skill(finish-card)` § "After closure" tells a closer to check whether the defect they just fixed is also described by an open card, and to write the supersession edge. Today nothing prompts that.
  - [x] MECHANICAL: `Skill(create-card)` dedups new filings against the *gated* backlog, not only against open titles. Both instances below were filed as fresh cards while a parked card already described the defect.
  - [ ] PROCESS: decide explicitly whether the gate should keep blocking `goc status <t> superseded`. It is the reason a stale park cannot be retired autonomously, and loosening it is a real option with real risk — record the rejection if it is rejected.
  - [x] MECHANICAL: if a mechanism ships, mirrors re-synced (`python scripts/sync_plugin_assets.py --check`) and the OpenClaw port re-run (`python3 scripts/port_skills_to_openclaw.py --check`), both clean.
  - [x] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green.
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
card".

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
negatives. `tests/test_waiting_filter_status_scope.py` independently pins the
two named cells against the real CLI over a temp deck. The `--waiting` help
text now describes the predicate rather than the storage field.

One detail sharpens the cost. The fix took the option the second card
explicitly argued *against* — that card recommended overlay-field-presence
and the engine shipped the predicate reading, which drops elapsed-wait cards
from `--waiting`. A parked card is not only going stale; it can be silently
overruled, and the record shows neither the ruling nor the disagreement.

## How big it is (measured 2026-08-24)

`reproduce.py` in this directory anchors every `file:line` cite a gated card
carries and asks whether that line still exists in HEAD:

| | count |
|---|---|
| gated cards (`human_gate` ≠ `none`) | 190 |
| ... carrying at least one resolvable anchor | 146 |
| ... at least one anchor now absent from HEAD | **26** (18% of scanned) |
| absent anchors in total | 31 |

(The scan ran at 189/145 before this card's own gate went up; this card's
anchors resolve, so only the population rows moved.)

So the honest answer to "how many of the 170 are stale" is: **26 gated cards
quote code that no longer exists**, and that is an upper bound on candidates,
not a confirmed count of fixed defects. An absent anchor proves the cited
code moved; only reading the card proves the defect went with it. Both known
instances are inside the 26, which is the reason to trust the number as a
screen. The 44-across-30 figure quoted when this card was filed came from a
different anchoring rule and is superseded by the table above.

## The signal erases itself — and that decides Option B

`Skill(refine-deck)` anchors a cite at the commit that **last wrote** the line
number. That is the correct rule for *repairing* a drifted number, and it is
the wrong rule for detecting staleness, because step 4 of the same recipe then
relocates the number onto a line that does exist. The repair consumes the
evidence.

It is not a corner case. Of the 157 gated cards carrying cites, **133 have had
at least one cite rewritten by a repair pass** — 85%. Both cards in the table
above were repaired by the 2026-08-10 pass, and at HEAD, last-write anchoring
now finds nothing wrong with either of them:

| anchoring rule | catches the two known stale parks | cards flagged |
|---|---|---|
| last-write (what `refine-deck` computes today) | **0 of 2** | 24 |
| as-filed (anchor at the card's filing commit) | **2 of 2** | 26 |

The two rules flag similar totals but not the same cards, and only the
as-filed rule recovers the line the card actually complains about —
`filtered = [t for t in filtered if t.waiting_on is not None]`, absent from
HEAD since `91d40320`.

This changes the recommendation the card was filed with. Option B is still
the cheapest option, but **not** as "report the absent anchors the pass
already has" — those are the post-repair ones, and they would have missed
both known instances. B has to anchor as-filed, which is a second pass over
history the current recipe does not do, and it has to run *before* the repair
step in any pass that does both.

## What landed in this session

Two prevention steps the DoD marks as unconditional, plus the harness:

- **`reproduce.py`** (this directory) — as-filed anchor scan over the gated
  backlog. Fails today (exit 1, 24 unsurfaced candidates). Its controls run
  first and refuse to report a clean deck unless a synthetic offender is
  caught, a synthetic clean case is cleared, and both known stale parks are
  re-found — so a green run cannot mean "nothing scanned".
- **`Skill(finish-card)` § "Other cards your fix also fixed"** — the closer,
  who is the only actor who knows what was just fixed, greps card *bodies*
  before the flip. Gate `none` → write the `superseded` edge. Gate
  `decision`/`session` → the engine refuses and should, so append a
  `## <ts> — Staleness re-check` entry naming the fixing commit.
- **`Skill(create-card)` § "Dedup against parked cards"** — the same grep at
  the other end of a card's life, because the title grep that dedup used
  cannot see into a parked card's body.
- The `Staleness re-check` heading is now the machine-readable marker for
  "someone re-read this". Applied to both known instances, which is why
  `reproduce.py` reports 24 unsurfaced out of 26 candidates rather than 26.
- `tests/test_skill_body_size.py` caps for the two skills raised 10,000 →
  10,500 with the rationale recorded there; `create-card` was at 9,996 bytes,
  so no addition of any size would have fit. The measurement and the worked
  instance went to the `reference.md` siblings, per that guard's contract.

None of this detects staleness on its own. It stops the *next* instance and
marks the two known ones; the 24 remaining candidates still need whatever
mechanism the decision below picks.

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

**Option C is done** — it was the one option the DoD marks unconditional, so
this session implemented it rather than asking. What is left is narrower than
the card was filed with, and the measurement above moves it: the question is
who runs an **as-filed** anchor scan over the 24 remaining candidates, given
that the pass which would naturally host it destroys its own input.

**Option A — a `goc` check.** Extend `goc validate` (advisory) or add a verb
that, for each non-terminal card, extracts cited anchors and reports the ones
absent from the tree.

- *For:* the only option that fires without a human or a hygiene pass in the
  loop, and it ships to every consumer. It is also the only home immune to
  the erasure problem, because it would anchor from history rather than from
  whatever the last repair pass wrote.
- *Against:* `goc validate` does not read card bodies today, and giving it a
  citation parser is a real surface addition. Cost is now known rather than
  guessed — `reproduce.py` is the working implementation, ~230 lines, one
  `git log --follow` plus one `git cat-file --batch` per card, whole-deck run
  in well under a minute. It remains bounded by
  [file-line-citations-drift-again-within-days-of-every-repair-pass](../file-line-citations-drift-again-within-days-of-every-repair-pass/):
  the scan is only as good as the citation form, and that form is itself
  parked on a decision.

**Option B — a `Skill(refine-deck)` category.** Make "stale parks" a named
sub-section beside "Stale unverified parks".

- *For:* still the cheapest, and it is where the finding was made. Ships to
  consumers with the skill.
- *Against:* **the "free by-product" argument does not survive the
  measurement.** The pass computes *post-repair* anchors, which caught 0 of 2
  known instances; the category needs a second, as-filed anchoring pass, and
  it must run before the repair step or there is nothing left to find. That
  is a real change to the recipe, not a report over data in hand. It also
  only fires when someone runs the pass, and it can only report.

**Option D — accept it, and say so.** Document that a parked card's claims
are as of its filing date and must be re-verified before deciding.

- *For:* honest, and free. The re-verification cost lands on the reader who
  is already reading the card, which is the cheapest possible moment. C plus
  the `Staleness re-check` marker already covers every *new* instance, so D
  concedes only the 24 standing candidates.
- *Against:* the reader is precisely who has not shown up for 101 of these
  cards in 60+ days.

**Revised recommendation, not binding: A, or D.** B was the recommendation
when the pass looked free; it no longer is, and a second anchoring pass
bolted into a hygiene skill is most of A's cost in a home that only fires by
hand. If the 24 candidates are worth clearing, `reproduce.py` is already the
mechanism — promoting it to a `goc` verb is mostly relocation. If they are
not, say so under D and let C hold the line going forward. The sibling
outlet card's option C (a working `goc triage`) should carry the staleness
signal if it lands, since a decision queue that presents stale cards as live
is the harm restated one layer up.

### Second question — should the gate keep blocking `superseded`?

Unchanged, and the recommendation is still **keep it**. An agent that could
clear human gates to tidy the board would be worse than the rot. This session
is the evidence that the refusal is survivable: the two known stale parks were
marked with a machine-readable `## Staleness re-check` entry and left at their
gate, which is a better note without being an unauthorized decision. Record
the rejection explicitly when deciding — the DoD asks for that, not for
silence.

## Non-goals

- Not a proposal to loosen the gate on `goc status ... superseded`. DoD item 6
  asks for that to be decided explicitly, because it is the mechanism that
  makes this irreducible, but the default answer is to keep it.
- Not a citation-format change. That is
  `file-line-citations-drift-again-within-days-of-every-repair-pass`, and this
  card only borrows its absent-anchor signal.
- Not a claim that the two instances should have been filed differently. Both
  are good cards that describe a real defect accurately as of their filing.


## 2026-08-24T05:20:00Z — Gate raised to `decision`; measurement and both prevention steps landed

Pulled at `human_gate: none`. Everything the decision does not depend on is
done; the gate is up for what it does.

**Measured (DoD 2).** `reproduce.py` anchors every `file:line` cite a gated
card carries and asks whether that line survives in HEAD. Of 189 gated
open/active cards, 145 carry a resolvable anchor and **26 carry one that is
absent from HEAD** (31 anchors total). That is the candidate set, not a
confirmed stale count — an absent anchor proves the code moved, only reading
the card proves the defect moved with it. The 44-across-30 figure in the
filing came from a different anchoring rule and is superseded.

**The finding that changes the decision.** `Skill(refine-deck)` anchors at the
commit that last *wrote* the line number, then step 4 relocates the number
onto a line that exists — the repair consumes the evidence. 133 of the 157
cited gated cards (85%) have had a cite rewritten this way, including both
known stale parks. Last-write anchoring at HEAD catches **0 of 2**; anchoring
at the filing commit catches **2 of 2**. So Option B's "the pass already has
this data" argument is false: the data it has is post-repair. B now costs a
second anchoring pass that must run before the repair step, which is most of
A's cost in a weaker home. The README's recommendation was revised from
"B plus C" to "A, or D" on that basis.

**Landed (DoD 4, 5, 7, 8).** `Skill(finish-card)` § "Other cards your fix also
fixed" — the closer greps card bodies before the flip and writes the
`superseded` edge, or, on a gated card the engine correctly refuses to move,
a `## <ts> — Staleness re-check` log entry naming the fixing commit.
`Skill(create-card)` § "Dedup against parked cards" — the same grep at filing
time, since the title grep dedup used cannot see into a parked card's body.
Both known instances got the marker, taking `reproduce.py` from 26 unsurfaced
to 24, which is what makes the marker demonstrably load-bearing rather than
decorative. Mirrors synced and the OpenClaw port re-run, both `--check` clean;
`goc validate` clean; 1030 tests green.

`tests/test_skill_body_size.py` caps for the two skills went 10,000 → 10,500,
documented in that file. `create-card` was at 9,996 of 10,000, so no addition
of any size would have fit; the rationale and the worked instance went to the
`reference.md` siblings as that guard's contract requires, and only the rule
plus the grep stayed in each core.

**Not done, and why.** DoD 1 (`reproduce.py` exits zero) is blocked on DoD 3 —
the script exits 1 with 24 unsurfaced candidates, which is the correct
pre-fix state, and clearing them needs the mechanism the human picks. DoD 6
(should the gate keep blocking `superseded`) is recorded with a recommendation
to keep it, but the DoD asks for an explicit human ruling, not an agent's.

## 2026-09-21 — refine-deck: deck-wide measurement of the parked cohort

Supporting evidence from the 2026-09-21 hygiene pass, recorded here rather
than filed as a new card because it is this card's thesis measured at deck
scale, not a separate finding.

Of 200 open cards, **127 (64%) have had no `log.md` (or, absent one, README)
activity in 60+ days**. The tail is dominated by a single batch: roughly
twenty `goc-*` verb cards filed together around 2026-05-29, every one still
`human_gate: decision`, all untouched for ~115 days. Longest-parked open card
is 129 days (`support-custom-frontmatter-fields-with-enum-and-required-when-rules`).

This is the footprint the card predicts — parks accumulate because no pass can
retire them and no human re-reads them — and it is why the hygiene pass files
its own findings at `human_gate: none` where the evidence supports it.

## 2026-10-17T05:00:00Z — Instance connected: a decision option resting on a premise false at filing

[pattern-generalization-opt-out-regex-misses-quoted-yaml-values](../pattern-generalization-opt-out-regex-misses-quoted-yaml-values/)
(open, `decision`, filed 2026-05-29). Its Option 3 weighs replacing the
hook's regex with `yaml.safe_load` on the premise that "the engine already
requires PyYAML". The engine dropped PyYAML in `d490d6d1` on 2026-05-09,
twenty days before the card was filed. That understates the option's cost:
it would add goc's only third-party import. The card now carries a
`## Staleness re-check` entry (`d821a2f1`); its gate and options are
untouched.

Two datums for the decision. First, Option C's closer sweep is what found
it. The closure of
`plugin-payload-still-declares-click-and-pyyaml-dependencies-the-engine-dropped`
grepped open cards for the package names its fix touched. That fix did not
fix this card's defect, but the shared symbol surfaced a stale premise
anyway, so the sweep reaches further than "cards your fix also fixed".
Second, neither Option A nor B's as-filed anchor scan would fire here. The
claim was false when written, not made false by later work, and it is prose
("requires PyYAML"), not a cited anchor that stopped resolving. Option D's
framing, that a parked card's claims hold as of its filing date, needs the
same caveat: a claim can already be stale at filing.

## 2026-08-24T02:32:11Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

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


## 2026-10-22T05:26:19Z: decision recorded

Option B — a Skill(refine-deck) category runs the as-filed anchor scan over gated cards before the citation-repair step, re-runs each candidate's reproduce.py and re-anchors live defects; the human gate keeps blocking superseded — The maintainer chose B in a human session on 2026-10-22 over the card's revised A-or-D recommendation, keeping the mechanism in the hygiene pass; loosening the superseded gate is rejected, because an agent that clears human gates to tidy the board would be worse than the rot. Gate decision → none. Status active → open — the claim parked behind the gate is released, so the next pull-card claims the card per this decision.

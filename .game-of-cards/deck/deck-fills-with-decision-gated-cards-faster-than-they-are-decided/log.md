# log

## 2026-08-17 — pull session: census re-scored the options; gate raised to `decision`

Claimed, measured, and parked. No code changed.

**What was measured.** The filing assumed the gated pile was largely
accidental — that `human_gate_default: decision` had swept in filings nobody
gated on purpose. A census of all 185 gated live cards (not a sample) checked
each for the `## Decision required` section that `Skill(card-schema)`
§ "Decision-gate body contract" requires whenever an agent chooses a
`decision` gate:

```
gated live cards: 185
  with a '## Decision required' section: 160   (decision 156, session   4)
  without one:                            25   (decision  10, session  15)
stale 60d+ among the 160 with a section: 72
stale 60d+ among the 25 without:         11
contribution mix of the 185: high 35, medium 135, low 15
```

94% of the decision gates carry the deliberate-gate artefact, and 15 of the
19 session gates are roadmap epics for which an options matrix was never the
right shape. `reproduce.py` still exits 1 (runway 8 against a floor of 15),
so the defect is real — but its mechanism is not the one the card names.

**What that changed.** The defect moved from intake to outlet. Option A
(flip the shipped default) would move at most 10 of 185 cards and still leave
the runway in single digits; option B is already 94% satisfied in practice.
Option C is the only one the evidence supports, and it is cheaper than filed:
`_cmd_triage` already reads the backlog with `--json` and per-card option
previews — what it lacks is ranking, a cap, and a decide loop. At 181 cards
it emits 1491 lines in creation order. Also noted while reading it: its
`--help` understates its scope (it silently filters to `status == "open"` and
to non-drafts, which is why it reports 181 of 185) — that is DoD item 5's
concern and stays with this card.

The README dashboard was rewritten in place with the census, and
`## Fix options` was replaced by a contract-shaped `## Decision required`
carrying both questions the DoD demands: where the fix goes, and what happens
to the 185 already gated.

**Why the gate went up rather than the decision going down.** Three reasons,
recorded in the body: option A edits a value shipped to every PyPI / npm /
ClawHub consumer and inverts the tool's default safety posture for repos
nobody here can see; option C's fidelity is bounded by
`decision-required-options-have-no-machine-readable-shape-and-parsers-keep-drifting`,
which is undecided; and this card's own body already says it should be
decided together with `autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish`,
whose prerequisite `human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property`
is undecided too. `.game-of-cards/hooks/pull-card.md` defines no project-local
consultation rubric, so `Skill(pull-card)`'s Andon cord routes this to the
human. Recommendation recorded in the body and not binding: C for question 1,
with the 10-card cleanup for question 2.

Status returned to `open` so the card appears in `goc triage`, where gated
cards are read; `worker` is left as the historical record of this session, not
as a live claim.

## 2026-08-24 — hygiene pass: the runway reached zero

Re-measured during a `Skill(refine-deck)` pass. No code changed, no gate
changed; the README dashboard was rewritten in place because its headline
number was stale in a way that understated the defect.

```
open + active cards: 194   (was 193)
  human_gate: none         5   (was 8)
  human_gate: decision   170   (was 166)
  human_gate: session     19   (was 19)
gated open cards with no log activity for 60+ days: 101/189   (was 83/185)
```

**The finding this pass adds.** `reproduce.py` reports `runway = 5`, but
`goc --ready` returns **no cards at all**. The script counts
`human_gate: none`; the engine's `card_is_ready` additionally excludes
impeded cards, unpublished drafts, and cards already claimed. All five of the
gate-free cards fail one of those tests — three carry `waiting_on`, one is
`active`, one is a deliberately-held draft. So the autonomous runway is not
short, it is exhausted, and the card had no row for that.

Two consequences worth separating:

1. It does not change the option set. The census still says the backlog is
   94% deliberate decisions and the missing half is the outlet, so
   recommendation C (make `goc triage` a working decision queue) stands
   unaltered. What changed is urgency: there is no longer any autonomous
   work to do while the decision waits.
2. It is a defect in this card's own instrument, and DoD item 1 gates on that
   instrument — "the autonomous runway is at least 15 open cards" can go
   green with fifteen gate-free cards that are all impeded and a real runway
   of zero. That is the fail-open shape
   `static-source-guards-never-prove-they-can-catch-an-offender` describes,
   and the drifted-copy-of-the-ready-predicate shape that
   `extend-pull-readiness-coupling-invariant-to-the-board-not-ready-predicate`
   roots. Filed as
   `reproduce-py-runway-metric-counts-gates-instead-of-the-engine-ready-predicate`
   rather than fixed here, because editing the threshold test of a parked
   card changes what the card claims.

Also observed while measuring: 101 of the 189 gated cards are now 60+ days
without log activity, up from 83 of 185 a week ago, and at least two of them
describe defects that have since been fixed in code without anyone noticing
(see `parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them`).
So the gated pile is not merely unread — part of it is no longer true. That
sharpens option C: an outlet that only ranks and caps would still present
stale cards as live decisions.

## 2026-08-24 — instrument repaired: the runway now reads the engine predicate

`reproduce.py` no longer measures the runway with a `human_gate` count. It
calls `goc --ready --json` — the exact surface `Skill(pull-card)` selects
with — and reports the gate count beside it as the explicit upper bound.
Fixed under
`reproduce-py-runway-metric-counts-gates-instead-of-the-engine-ready-predicate`,
whose own `reproduce.py` is the falsifying probe: it runs a verbatim copy of
this script against a synthetic deck of 16 gate-free cards that are all
impeded, claimed, or unpublished, plus a control deck with three genuinely
pullable cards.

**Both numbers, measured on this deck today (DoD item 5 of the fixing card):**

```
gate-none cards (upper bound on the runway):   6
autonomous runway (goc --ready, claimable):    0
```

The upper bound reads 6 rather than the 5 recorded earlier today because the
fixing session claimed the deck's one remaining ready card; the runway is 0
either way, which is the number the exit code now gates on. Before the fix
the same deck reported `runway: 5` and the same deck today would report 6 —
never 0. Against the synthetic fail-open deck the pre-fix script printed
`PASS: runway of 16 cards is above the 15-card floor` and exited **zero**
while `goc --ready` returned nothing; the fixed script prints `runway 0`
against a gate-none upper bound of 16 and exits 1.

DoD item 1 was rewritten to gate on the engine predicate, so that pass state
is no longer reachable. Nothing else about this card changed: the option set,
the census, and the recommendation are untouched — the instrument was wrong,
not the argument.

**Sweep of sibling deck scripts (DoD item 6 of the fixing card).** All 439
`reproduce.py` files under `.game-of-cards/deck/` were scanned for a
`human_gate` comparison standing in for pullability, then for the words
runway / pullable / claimable / ready appearing with no engine seam.
**One offender: this script.** Ten scripts mention the gate outside a
frontmatter fixture; each was read:

| how the gate is used | scripts | verdict |
|---|---|---|
| `runway = gates.get("none", 0)` | 1 (this one) | **the drift** |
| fixture value or prose only, no pullability computed | 4 | clean |
| second conjunct beside the engine's own `ready` field | 2 | clean |
| reproducing `_cmd_triage`'s parked-card filter, where `human_gate != none` IS the predicate under test | 1 | clean |
| mirroring the engine's leverage-line gated set, pullability from `card_is_ready` | 1 | clean |
| counting the gated complement for a staleness census | 1 | clean |

Zero siblings carry the drift. Reported rather than assumed, because a silent
sweep is the failure mode the fixing card is an instance of.

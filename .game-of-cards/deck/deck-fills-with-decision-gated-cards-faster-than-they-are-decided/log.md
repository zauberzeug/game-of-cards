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

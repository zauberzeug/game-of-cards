---
title: deck-fills-with-decision-gated-cards-faster-than-they-are-decided
summary: "The runway has reached zero. Re-measured 2026-08-24 with a runway metric that now reads the engine predicate instead of counting gates: 5 of 195 live cards sit at human_gate none, 171 are gated on decision and 19 on session — and goc --ready returns NO cards at all, because every one of the 5 is impeded, claimed, or an unpublished draft. Measuring the backlog rather than the default relocates the defect: 94% of the decision-gated cards already carry a '## Decision required' section, so the gate is deliberate and the missing half is the outlet, not the intake. Nothing consumes the 190 — 99 have had no log activity for over 60 days. Parked 2026-08-17 on the intake-vs-outlet choice; the runway hitting zero does not change the options, only the urgency."
status: open
stage: null
contribution: high
created: "2026-08-17T02:58:07Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — `goc --ready` returns at least 15 claimable
    cards. The threshold reads the engine's `card_is_ready`, NOT the `human_gate:
    none` count the script reports alongside it as the runway's upper bound; 15
    gate-free cards that are all impeded, claimed, or drafts must NOT clear this
    item. See
    [reproduce-py-runway-metric-counts-gates-instead-of-the-engine-ready-predicate](../reproduce-py-runway-metric-counts-gates-instead-of-the-engine-ready-predicate/).
  - [ ] PROCESS: a mechanism is chosen from `## Decision required` question 1 and recorded in `log.md` with its rationale. Question 2 must be answered explicitly — what happens to the 185 cards already gated, not only to newly filed ones.
  - [ ] TDD: a regression test pins the chosen filing behaviour — a finding filed without an explicit `--gate` lands where the decision says it should, and one filed with `--gate decision` still lands gated. It must fail on today's default.
  - [ ] MECHANICAL: `goc/schema.yaml` and `Skill(create-card)` Step 3 agree with each other and with the implemented default; today the skill calls `decision` "the *fallback*" while the schema makes it the value you get by omission.
  - [ ] MECHANICAL: if the fix adds a triage surface for the gated backlog, `goc --help` describes its real scope, and the mirrors regenerate — `python scripts/sync_plugin_assets.py --check` and `python3 scripts/port_skills_to_openclaw.py --check` clean.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass.
worker: {who: "claude[bot]", where: main}
---

# The deck fills with decision-gated cards faster than they are decided

## Location

- `goc/schema.yaml:27` — `human_gate_default: decision`.
- `goc/templates/skills/create-card/SKILL.md` § Step 3 — "The CLI default is `decision` — the *fallback* for findings whose fix path genuinely needs a human pick."
- `goc/templates/skills/next-card/SKILL.md` — filters to `human_gate: none` for loop safety; that filter is what the runway below measures.

## What's broken

The deck has two intakes and one outlet. Findings arrive continuously —
`Skill(audit-deck)` files one most days, hygiene passes file more — and by
default they arrive gated. Gates are cleared by a human running
`Skill(decide-card)`, and on this repo that happens rarely. The result is
not a slow imbalance; the queue has now emptied completely:

| | 2026-08-17 | 2026-08-24 |
|---|---|---|
| open + active cards | 193 | 195 |
| `human_gate: none` (upper bound) | 8 | **5** |
| `human_gate: decision` | 166 | 171 |
| `human_gate: session` | 19 | 19 |
| gated cards with no log activity for 60+ days | 83 | 99 |
| **cards `goc --ready` actually returns (the runway)** | — | **0** |

The last row is the one that matters, and it is a number this card was not
measuring a week ago. The gate count is an *upper bound* on the runway, not
the runway: `card_is_ready` also excludes impeded cards, drafts, and cards
already claimed. All five of the `human_gate: none` cards fail one of those:

| card | why it is not pullable |
|---|---|
| `openclaw-plugin-skills-force-repeated-reads-every-session` | `status: active` (claimed) + `waiting_on: external` |
| `openclaw-subagent-plugin-tools-alsoallow-ignored` | `waiting_on: external` — upstream OpenClaw release |
| `blocked-status-conflates-dependency-external-wait-and-deferral` | `waiting_on: deferred` |
| `remove-blocked-from-status-enum-and-migrate-existing-cards` | `waiting_on: deferred` |
| `escalate-repeatedly-auto-released-cards-without-an-attempt-counter` | `draft: true`, held deliberately |

So `goc --ready` prints `No cards match`. The autonomous runway is not
"a few days" — it is exhausted, and has been since before this measurement.
The other 190 are invisible to `Skill(pull-card)` and `Skill(next-card)`,
which filter to `human_gate: none` — correctly, for loop safety.

This card's own `reproduce.py` did not measure that until 2026-08-24: it
reported `runway = gates.get("none", 0)`, a bare gate count, which said 5
where the engine said 0 — so DoD item 1 could have gone green on 15 gate-free
cards the picker could not touch. Fixed by
[reproduce-py-runway-metric-counts-gates-instead-of-the-engine-ready-predicate](../reproduce-py-runway-metric-counts-gates-instead-of-the-engine-ready-predicate/):
the runway is now `len(goc --ready --json)` and the gate count is reported
next to it as the upper bound, so the two are never read as one number again.

The default was the first suspect. `goc/schema.yaml:27` sets
`human_gate_default: decision`, and `_build_parser`'s `p_new.add_argument
("--gate", …)` in `goc/engine.py` hands that value to every card filed
without an explicit `--gate` — it is the field's only consumer. So the two
states

- "I considered the gate and a human really must pick"
- "the gate never came up"

are written to disk identically, and the filer who thought about neither
lands in the same bucket as the filer who thought hard.

Measuring the backlog instead of the default narrows that sharply. Every one
of the 185 gated live cards was checked for a `## Decision required`
section — the artefact `Skill(card-schema)` § "Decision-gate body contract"
requires whenever an agent *chooses* a `decision` gate, and therefore a
usable proxy for "the gate was deliberate":

| | with `## Decision required` | without |
|---|---|---|
| `human_gate: decision` (166) | **156** | 10 |
| `human_gate: session` (19) | 4 | 15 |

Only 10 of 166 decision gates look accidental, and 15 of the 19 session
gates are roadmap epics for which an options matrix was never the right
shape. In practice the two states *are* distinguishable, and the backlog is
overwhelmingly real undecided decisions rather than filings that never
considered the gate.

That relocates the defect. The intake is legitimate; the outlet is missing.
Changing what a card gets by omission would move at most 10 of 185 cards,
and would leave today's runway in the single digits. Nothing consumes the
other 175: 83 of the 185 have had no log activity in 60+ days, the oldest
was filed 2026-05-03, and 35 are `contribution: high`. `goc triage` is the
one surface that reads them, and at this size it emits 1491 lines in
creation order with no cap and no value ranking — a dump, not a working
queue.

## Empirical evidence

`reproduce.py`, re-run 2026-08-24 after its runway metric was repaired to read
the engine predicate:

```
open + active cards: 195
  human_gate: none         5
  human_gate: decision   171
  human_gate: session     19

gate-none cards (upper bound on the runway):   5
autonomous runway (goc --ready, claimable):    0
  5 gate-none cards are not claimable:
       2  impeded (waiting_on: deferred)
       1  claimed (status: active)
       1  impeded (waiting_on: external)
       1  unpublished draft

sample of 50 cards closed in the last 90 days:
  born gated, later decided and closed: 8
  born at gate=none:                    42

gated open cards with no log activity for 60+ days: 99/190

DEFECT PRESENT: the picker has 0 claimable cards (gate-none upper bound 5) against
190 gated ones. Ungated cards close 5x more often than gated ones get decided, so
the backlog grows while the runway does not.
```

The first two numbers under the census used to be one number. Until 2026-08-24
the script reported `autonomous runway (gate=none, claimable by the picker): 5`
— a bare `human_gate` count — and nothing next to it. That number is the upper
bound, and on this deck the bound is the whole gap: every gate-free card is
excluded by one of the three axes `card_is_ready` also reads, so the runway is
zero and the reassuring 5 was measuring the wrong set. The two now sit side by
side and the exit code reads the lower one. `goc --ready` agrees from the
other side:

```
$ uv run goc --ready
No cards match (ready: status open, gate none, no active impediment;
1 unauthored draft scaffold hidden — author, then `goc publish <title>`).
```

The staleness share climbed across the same week: 99 of 190 gated cards have no
log activity in 60+ days (52%), against 83 of 185 (45%) on 2026-08-17. The
denominator grew and the share grew with it, so the gated pile is accumulating
faster than anything reads it.

The sample is the load-bearing part of the *rate* claim. It reads each closed
card's *first* committed frontmatter, so it distinguishes a card that was
born ungated from one that was gated and later decided — a distinction the
current frontmatter cannot show, because `decide` lowers the gate in place
and all 519 closed cards therefore read `human_gate: none` today.

The second measurement is what reframes the card (2026-08-17 pull session,
census of all 185 gated live cards, not a sample):

```
gated live cards: 185
  with a '## Decision required' section: 160   (decision 156, session   4)
  without one:                            25   (decision  10, session  15)

stale 60d+ among the 160 with a section: 72
stale 60d+ among the 25 without:         11
contribution mix of the 185: high 35, medium 135, low 15
oldest gated card: created 2026-05-03
```

The original filing assumed the gated pile was largely accidental — that the
default had swept in filings nobody gated on purpose. It has not: 94% of the
decision gates carry the deliberate-gate artefact. The defect survives, but
it is an outlet problem, not an intake problem, and the fix options below are
re-scored accordingly.

## Why it matters

The immediate cost is that the autonomous loop runs out of work. When the
runway empties, the loop either idles or reaches for whatever is left
regardless of fit, and the deck stops being a scheduler.

The larger cost is that the gated backlog is not a queue, because nothing
consumes it. 83 of 185 gated cards have had no log activity in 60+ days and
the oldest are past 100. Those cards were expensive to produce — most carry
a `reproduce.py` and a worked options section — and they are accumulating in
a place where the only reader who could act on them is the one who is not
reading. That is a slower, quieter version of the failure
[a-shared-tag-groups-a-cluster-that-no-edge-walk-can-reach](../a-shared-tag-groups-a-cluster-that-no-edge-walk-can-reach/)
describes for tag-grouped clusters: work that is correctly filed and
practically unreachable.

This is the opposite failure from
[autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish](../autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish/),
which is about cards that reach the picker at `gate: none` when they should
not. Both are symptoms of the gate being a single card-level flag set once at
filing time; the two cards should probably be decided together, and the
prerequisite that one names
([human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property](../human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property/))
constrains this one as well.

## Decision required

Filed at `human_gate: none` per this repo's autonomous-filing convention and
raised to `decision` by the 2026-08-17 pull session, which measured the
backlog and could not responsibly pick for three reasons. Option A edits a
value shipped in `goc/schema.yaml` to every PyPI / npm / ClawHub consumer, so
it inverts the tool's default safety posture for repos nobody here can see.
Option C's usefulness is bounded by
[decision-required-options-have-no-machine-readable-shape-and-parsers-keep-drifting](../decision-required-options-have-no-machine-readable-shape-and-parsers-keep-drifting/),
which is itself undecided. And this card's own body already records that it
should be decided together with
[autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish](../autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish/),
whose stated prerequisite
[human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property](../human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property/)
is also undecided — picking here in isolation would pre-empt two parked
cards rather than resolve them.

### Question 1 — where does the fix go?

**Option A — stop defaulting to a gate.** Set `human_gate_default: none` and
make `decision` opt-in.

- Pros: the two states become distinguishable at the source; every future
  ungated-by-omission filing lands on the runway.
- Cons: the census says this is now the *weakest* option here — it addresses
  10 of 185 cards, leaves the runway in single digits, and hands every
  downstream consumer the failure that
  `autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish`
  describes. Only safe paired with something that catches an unanswerable
  DoD, which is exactly the undecided prerequisite card.
- Edit: `goc/schema.yaml:27` plus its byte-identical twin
  `goc/templates/skills/card-schema/schema.yaml:27` (parity is enforced by
  `tests/test_skill_schema_yaml_parity.py`); no engine change — the field's
  sole consumer is `p_new.add_argument("--gate", …)` in `_build_parser`.

**Option B — make the gate a claim the filer has to earn.** Keep the
default; have `goc validate` warn (or `goc new` refuse) when a
`decision`-gated card carries no `## Decision required` section.

- Pros: separates the two states without touching anyone's default; the
  option-shape card's DoD item 6 already proposes this warning for an
  unrelated reason, so it lands once and serves both.
- Cons: the census says the deck is already 94% compliant, so it would flag
  10 decision-gated cards and change nothing about the runway. It is
  hygiene, not the fix.
- Edit: a new check in `validate_card` / the validator walk in
  `goc/engine.py`, reusing `extract_decision_required_section`.

**Option C — give the backlog an outlet instead of a smaller intake.** Make
`goc triage` a working decision queue rather than a dump: rank by
contribution and staleness, cap the default output, and add a decide loop
that walks cards and calls `goc decide` per card.

- Pros: the only option the census actually supports — 175 of the 185 are
  real decisions whose sole cost is that reading them costs 1491 lines in
  creation order. Most of the surface exists already
  (`_cmd_triage` in `goc/engine.py`, with `--json` for Q&A consumers and
  `extract_decision_required_section` for previews), so this is largely
  ranking, capping, and a loop.
- Cons: the preview fidelity depends on the undecided option-shape card; and
  it treats the symptom — intake keeps producing, so it needs re-running.
- Edit: `_cmd_triage` and its subparser (`p_triage`, `goc/engine.py:4068`),
  whose `--help` string — "List parked cards (gate ≠ none), grouped by gate,
  oldest-first" — also understates its real scope today: it silently filters
  to `status == "open"` and to non-drafts, which is why it reports 181 of the
  185 gated cards.

### Question 2 — what happens to the 185 already gated?

The DoD requires this answered explicitly; any option that only changes new
filings leaves today's runway at eight.

1. **Nothing structural — route them through the outlet.** They are real
   decisions (156/166 carry the artefact); they need reading, not
   re-labelling. Implies C.
2. **Bulk-lower the 10 decision-gated cards with no `## Decision required`
   section.** The only subset the evidence marks as plausibly
   gated-by-omission. Small, reversible, and reviewable card-by-card.
3. **Bulk-lower all 185.** Rejected by the census — it would discard a
   deliberate signal on 160 cards and hand the picker work it cannot finish.
4. **Prune by age.** Close or disprove the 83 stale ones unread. Cheapest,
   and destroys the most: 72 of the 83 carry a worked options section, and
   35 of the 185 are `contribution: high`.

### Recommendation

Not binding: **C for question 1, with 2 as the one-time cleanup** — the
census moved the defect from intake to outlet, and 175 cards whose only
problem is that nobody can read them cheaply are fixed by making them
readable, not by re-labelling them. Doing B alongside is nearly free and
keeps the 94% honest. A should wait for
`human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property`,
which may make the card-level flag moot.

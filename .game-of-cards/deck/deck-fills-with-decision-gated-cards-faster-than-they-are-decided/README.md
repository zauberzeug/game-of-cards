---
title: deck-fills-with-decision-gated-cards-faster-than-they-are-decided
summary: "Only 8 of 193 open cards sit at human_gate none; 166 are gated on decision and 19 on session, so the autonomous picker has a runway of days against a backlog of months. The gate is the schema default, which makes 'nobody chose a gate' indistinguishable from 'a human must pick'. Sampling 50 cards closed in the last 90 days, 44 were born ungated and 6 were born gated and later decided, and 83 of the 185 gated cards have had no log activity for over 60 days."
status: active
stage: null
contribution: high
created: "2026-08-17T02:58:07Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — the autonomous runway is at least 15 open cards.
  - [ ] PROCESS: a mechanism is chosen from `## Fix options` and recorded in `log.md` with its rationale. The choice must say explicitly what happens to the 185 cards already gated, not only to newly filed ones.
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
not a slow imbalance; it is a queue that has already emptied:

| | count |
|---|---|
| open + active cards | 193 |
| `human_gate: none` — the entire autonomous runway | **8** |
| `human_gate: decision` | 166 |
| `human_gate: session` | 19 |
| gated cards with no log activity for 60+ days | 83 |

Eight claimable cards is a few days of loop. Two of those eight were filed
by the pass that wrote this card. The other 185 are invisible to
`Skill(pull-card)` and `Skill(next-card)`, which filter to `human_gate: none`
— correctly, for loop safety.

The mechanism is a default rather than a decision. `create-card` describes
`decision` as *the fallback for findings whose fix path genuinely needs a
human pick*, and that description is right. But `goc/schema.yaml:27` also
makes it the value a card gets when nobody supplies one, so the two states

- "I considered the gate and a human really must pick"
- "the gate never came up"

are recorded identically and are afterwards indistinguishable. Every filing
that does not think about the gate lands in the same bucket as the ones that
did, and that bucket is unreachable by the only mechanism draining the deck.

Nothing here is a wrong gate on any individual card. Sampling the gated
cards, most of them do name a real decision in a `## Decision required`
section. The defect is in the aggregate: a fallback that is also a default
will collect everything, and no surface reports that the queue behind it has
grown past what anyone will ever read.

## Empirical evidence

```
open + active cards: 193
  human_gate: none         8
  human_gate: decision   166
  human_gate: session     19

autonomous runway (gate=none, claimable by the picker): 8

sample of 50 cards closed in the last 90 days:
  born gated, later decided and closed: 6
  born at gate=none:                    44

gated open cards with no log activity for 60+ days: 83/185

DEFECT PRESENT: the picker has 8 claimable cards against 185 gated ones. Ungated cards
close 7x more often than gated ones get decided, so the backlog grows while the runway
does not.
```

The sample is the load-bearing part. It reads each closed card's *first*
committed frontmatter, so it distinguishes a card that was born ungated from
one that was gated and later decided — a distinction the current frontmatter
cannot show, because `decide` lowers the gate in place and all 519 closed
cards therefore read `human_gate: none` today.

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

## Fix options

Filed at `human_gate: none` per this repo's autonomous-filing convention.
The choice below is real and a reader who wants to make it deliberately
should raise the gate and record it via `Skill(decide-card)`.

**A. Stop defaulting to a gate.** Change `human_gate_default` to `none` and
make `decision` something a filer opts into. The two states above become
distinguishable immediately, and the runway recovers for new work. Cost:
findings that genuinely need a pick will sometimes reach the picker
ungated — the exact failure the sibling card is about — so this is only safe
paired with something that catches an unanswerable DoD.

**B. Make the gate a claim the filer has to earn.** Keep the default, but
have `goc validate` warn (or `goc new` refuse) when a `decision`-gated card
carries no `## Decision required` section naming credible options. That
separates the two states without changing anyone's default, and there is
already a card asking for this warning for a different reason —
[decision-required-options-have-no-machine-readable-shape-and-parsers-keep-drifting](../decision-required-options-have-no-machine-readable-shape-and-parsers-keep-drifting/)
DoD item 6 proposes exactly it. Cost: does nothing about the 185 already
filed.

**C. Give the backlog an outlet instead of a smaller intake.** Add a
batch-decide surface — the gated cards, their options, one pass — so clearing
gates costs a session rather than 185 individual reads. Cost: it depends on
the option shape being parseable, which is the open card named above; and it
treats the symptom, so the intake keeps producing.

Whichever is chosen, the DoD asks it to state what happens to the 185
existing cards. Any option that only changes new filings leaves today's
runway at eight.

---
title: reproduce-py-runway-metric-counts-gates-instead-of-the-engine-ready-predicate
summary: "The reproduce.py of deck-fills-with-decision-gated-cards-faster-than-they-are-decided measures its autonomous runway as runway = gates.get(\"none\", 0) — a bare human_gate count over open+active cards. The engine's card_is_ready also excludes impeded cards, unpublished drafts, and cards already claimed. On 2026-08-24 the script reported runway 5 while goc --ready returned no cards at all, so the card's DoD gate (runway at least 15) can go green with a real runway of zero. Seventh known hand-rolled copy of the pull-readiness predicate, and a fail-open defect test."
status: done
stage: null
contribution: medium
created: "2026-08-24T02:31:19Z"
closed_at: "2026-08-24T05:10:06Z"
human_gate: none
advances:
  - extend-pull-readiness-coupling-invariant-to-the-board-not-ready-predicate
advanced_by: []
tags: [bug, test, api-contract]
definition_of_done: |
  - [x] TDD: a falsifying probe exits non-zero on today's script — construct a deck (or a stub card list) with 15+ `human_gate: none` cards that are all impeded, drafts, or `active`, and show the current `runway` metric reports 15+ while `card_is_ready` reports 0. It must exit zero after the fix.
  - [x] MECHANICAL: `reproduce.py` in `deck-fills-with-decision-gated-cards-faster-than-they-are-decided` derives its runway from the engine — either by shelling out to `goc --ready --json` or by importing `card_is_ready` — rather than counting `human_gate`. It already shells out to `goc` for the card list, so no new dependency is introduced.
  - [x] MECHANICAL: the gate count is kept as a *separate* reported line (it is the upper bound and the card's intake argument uses it), so the fix adds a number rather than replacing an argument.
  - [x] MECHANICAL: the parent card's `## Empirical evidence` block and its `## What's broken` table are re-rendered from the fixed script, and DoD item 1 there ("the autonomous runway is at least 15 open cards") reads against the engine predicate.
  - [x] EMPIRICAL: run the fixed script on this repo's deck and record both numbers in that card's `log.md`. Today they are 5 and 0.
  - [x] PROCESS: decide and record whether the sibling deck scripts carry the same drift — a sweep of `.game-of-cards/deck/*/reproduce.py` for `human_gate` / `"none"` comparisons that stand in for pullability. Report the count even if it is zero; a silent sweep is the failure mode this card is an instance of.
  - [x] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green.
worker: {who: "claude[bot]", where: main}
---

# A card's runway metric counts gates where the engine counts pullability

## Location

- `.game-of-cards/deck/deck-fills-with-decision-gated-cards-faster-than-they-are-decided/reproduce.py`
  — was `runway = gates.get("none", 0)` at line 91; now `goc_json()` (line 64)
  plus `runway = len(goc_json("--ready"))` (lines 129-130), with the gate count
  kept as `gate_none` (line 122) and printed as the upper bound (line 137).
- `.game-of-cards/deck/reproduce-py-runway-metric-counts-gates-instead-of-the-engine-ready-predicate/reproduce.py`
  — the falsifying probe added by this card.
- `goc/engine.py:2582` — `card_is_ready`, the predicate the picker actually uses
- `goc/engine.py:2695` — `live_impeded`, one of the axes the script omitted

## What was broken

The script measured the autonomous runway with a one-axis count:

```python
gates = Counter(c["human_gate"] for c in live)
runway = gates.get("none", 0)
```

`live` is every card with `status in ("open", "active")`. The engine's
`card_is_ready` gates on four things, not one — status must be `open`
(so a claimed `active` card is out), the gate must be `none`, the card
must not be an unpublished draft, and it must carry no active impediment
overlay. Three of those four axes were missing from the script, so its
`runway` was an upper bound on the runway rather than the runway.

The gap is not theoretical, and it is widest exactly where the number
matters. Measured on this repo's deck, 2026-08-24:

```
$ uv run python .../reproduce.py
autonomous runway (gate=none, claimable by the picker): 5

$ uv run goc --ready
No cards match (ready: status open, gate none, no active impediment;
1 unauthored draft scaffold hidden — author, then `goc publish <title>`).
```

All five of the `human_gate: none` cards are excluded by an axis the script
does not read:

| card | axis that excludes it |
|---|---|
| `openclaw-plugin-skills-force-repeated-reads-every-session` | `status: active` + `waiting_on: external` |
| `openclaw-subagent-plugin-tools-alsoallow-ignored` | `waiting_on: external` |
| `blocked-status-conflates-dependency-external-wait-and-deferral` | `waiting_on: deferred` |
| `remove-blocked-from-status-enum-and-migrate-existing-cards` | `waiting_on: deferred` |
| `escalate-repeatedly-auto-released-cards-without-an-attempt-counter` | `draft: true` |

So the script printed 5 for a deck on which the picker could claim nothing.

## Why it matters

Two independent reasons, and the second is the one that makes this worth a
card rather than a one-line edit.

**It was a fail-open defect test.** The parent card's DoD item 1 read "TDD:
`reproduce.py` exits zero — the autonomous runway is at least 15 open cards."
Fifteen gate-free cards that are all impeded, claimed, or drafts satisfy that
with a real runway of zero: the card would close as fixed while the symptom it
was filed about — the loop having no work — was total. That is not a
hypothetical; the probe below demonstrates it, and the pre-fix script printed
`PASS: runway of 16 cards is above the 15-card floor` and exited zero on such a
deck. The witness could not distinguish "the runway recovered" from "the gate
count recovered", which is the two-passing-states shape
[static-source-guards-never-prove-they-can-catch-an-offender](../static-source-guards-never-prove-they-can-catch-an-offender/)
describes for prohibition scanners, arriving here through a threshold instead
of an empty list.

**It understated the defect it is evidence for.** The parent card argues that
the deck fills with gated cards faster than they are decided, and its
headline number is the runway. Reporting 5 rather than 0 made the situation
look like "a few days of loop left" when the correct reading is "the loop is
already starved". A dashboard that is wrong in the direction of reassurance is
worse than no dashboard.

## Family

This is the seventh known hand-rolled copy of the pull-readiness predicate,
and the first one inside the deck rather than in shipped code.
[extend-pull-readiness-coupling-invariant-to-the-board-not-ready-predicate](../extend-pull-readiness-coupling-invariant-to-the-board-not-ready-predicate/)
is the family root and enumerates copies one to five (`card_is_ready`,
`card_is_workable_for_scheduler`, the board's `not_ready` cell,
`.github/workflows/pull-card.yml`, and `render_empty_query_line`); the sixth
was the `standup` skill's "Next up" block, closed 2026-08-23 by
[standup-next-up-section-lists-cards-pull-card-would-never-pick](../standup-next-up-section-lists-cards-pull-card-would-never-pick/)
with the one-token substitution `goc` → `goc --ready`. That card measured
precision 0/3 against a true ready count of 0 — the same measurement, one day
earlier, on a different surface.

The root card's chosen fix shape ("expose the engine predicate, don't re-roll
it") applies unchanged, and the substitution here is the same size: the script
already shells out to `goc --status all --json`, so `goc --ready --json` costs
one more call and no new dependency. It is filed separately rather than folded
into the root because the root's DoD is about a Python introspection guard
over three in-engine copies, and a deck-local script is reachable by neither
that guard nor `goc validate`.

## Fix (applied)

`reproduce.py` now asks the engine. `goc_json()` wraps the subprocess call the
script already made (with `check=True`, so a failed invocation raises instead
of parsing an empty payload as "zero cards" — the same fail-open reading in a
different coat), and the runway is `len(goc_json("--ready"))`: the literal
surface `Skill(pull-card)` selects with. It is cross-checked against the
`ready` field the all-cards payload already carries — both are
`card_is_ready` — so a broken call shows up as a printed disagreement rather
than as a reassuring zero.

The gate count did not go away. It is now an explicitly labelled second line,
because it is the upper bound and the parent card's intake argument is about
it:

```
gate-none cards (upper bound on the runway):   6
autonomous runway (goc --ready, claimable):    0
  6 gate-none cards are not claimable:
       2  claimed (status: active)
       2  impeded (waiting_on: deferred)
       1  impeded (waiting_on: external)
       1  unpublished draft
```

The per-axis breakdown of the gap is new and free: it turns "the two numbers
disagree" into "here is which conjunct each excluded card fails", which is the
sentence the parent card's `## What's broken` table used to spell out by hand.

**The probe.** `reproduce.py` in this card's directory copies the target script
verbatim into a scratch repo whose `pyproject.toml` makes `_repo_root()` resolve
to the scratch tree, so the real artefact runs against a synthetic deck. Two
scenarios, and the second is the reason the first proves anything:

| scenario | deck | gate count | true runway |
|---|---|---|---|
| A — fail-open | 16 gate-free cards: 3 `waiting_on: external`, 3 `waiting_until: 2999-01-01`, 5 `active`, 5 `draft` (+2 gated) | 16 | 0 |
| B — control | scenario A plus 3 plain open ungated cards | 19 | 3 |

Scenario A is the falsification: the pre-fix script reports 16, clears its own
`MIN_RUNWAY = 15` floor and exits **zero** on a deck where `goc --ready`
returns nothing. Scenario B exists because a runway hardwired to 0 by broken
plumbing would sail through A — the probe requires the number to track the
engine when there *is* work. Both scenarios also assert the gate count is still
reported, so a future edit cannot "fix" the runway by deleting the upper bound.

Verified in both directions on 2026-08-24: the probe exits 1 against the
pre-fix script (all four assertions fail, including the `PASS: runway of 16`
line) and 0 against the fixed one.

**What changed in the parent card.** Its DoD item 1 now gates on `goc --ready`
returning 15+ claimable cards and says in as many words that 15 gate-free but
unpullable cards must not clear it. Its `## What's broken` table and
`## Empirical evidence` block are re-rendered from the fixed script, and
`log.md` carries both numbers plus the sweep result. Nothing about the parked
decision moved: the option set, the census, and the recommendation are
untouched. The instrument was wrong, not the argument — which is why this was
safe to do while the parent sits at `human_gate: decision`, and why the change
is confined to what the parent measures rather than what it concludes.

## Sweep of sibling deck scripts

DoD item 6 asked for the count even if it is zero. All 439 `reproduce.py` files
under `.game-of-cards/deck/` were scanned twice — once for a `human_gate`
comparison, once for the words runway / pullable / claimable / ready appearing
with no engine seam. Ten scripts touch the gate outside a frontmatter fixture;
each was read.

| how the gate is used | scripts | verdict |
|---|---|---|
| `runway = gates.get("none", 0)` | 1 | **the drift** — this card's target |
| fixture value or prose only, no pullability computed | 4 | clean |
| second conjunct beside the engine's own `ready` field | 2 | clean |
| reproducing `_cmd_triage`'s parked-card filter, where `human_gate != none` IS the predicate under test | 1 | clean |
| mirroring the engine's leverage-line gated set, pullability from `card_is_ready` | 1 | clean |
| counting the gated complement for a staleness census | 1 | clean |

**Zero siblings carry the drift.** The one offender is the one this card was
filed for. Worth recording *why*: the clean nine mostly reproduce an engine
predicate that genuinely is a gate test (triage's parked set, the leverage
line's gated candidates), and the two that ask about pullability read
`c["ready"]` straight out of `--json` — which the payload has carried since
before this deck existed. The drift needed a script that computed a
pullability number for its own purposes rather than testing an engine surface,
and exactly one script does that.

## Non-goals

- Not a change to `card_is_ready` or to any engine predicate. The engine was
  right; the script disagreed with it, and the script moved.
- No `tests/` regression test. The family root
  `extend-pull-readiness-coupling-invariant-to-the-board-not-ready-predicate`
  owns the in-engine introspection guard; a deck-local script is reachable by
  neither it nor `goc validate`, and wiring one of 439 `reproduce.py` files
  into CI would be a convention this repo does not have. The probe is the
  witness, and it is committed next to the card that explains it.
- Not the fix for the parent card's actual defect (the gated backlog has no
  outlet). That is parked on a human decision and unaffected by this.
- Not a general audit of deck scripts. DoD item 6 asks for the sweep's
  *count* precisely so that scope stays bounded and reported rather than
  silently skipped.

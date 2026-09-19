---
title: standup-waiting-on-you-section-omits-active-cards-parked-at-a-human-gate
summary: "The standup skill's Section 4 (\"Waiting on you\") promises \"all cards with human_gate: decision or session\" but runs `goc --json --status open`, so a card claimed and then parked behind a raised gate is dropped before the gate filter runs. On this repo's deck today that hides 5 of 197 live gated cards — every one of them a card an agent already tried and handed back to a human. Section 2 of the same file was fixed for the identical scope error on 2026-09-16 and now documents the principle Section 4 still violates."
status: done
stage: null
contribution: medium
created: "2026-09-19T04:35:04Z"
closed_at: "2026-09-19T04:40:06Z"
human_gate: none
advances:
  - active-state-conflates-being-worked-on-with-parked-at-human-gate
advanced_by: []
tags: [bug, api-contract, documentation]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — Section 4 reports `active-decision` and `active-session`, and still omits the ungated, terminal-stale-gate and draft controls.
  - [x] TDD: a regression test pins the Section 4 fenced block against the same (status x gate) grid, and statically asserts the block does not carry `--status open`, so the narrowing cannot return through a different status value. Mirrors `tests/test_standup_impeded_block_scope.py`, the Section 2 pin.
  - [x] MECHANICAL: the Section 4 command in `goc/templates/skills/standup/SKILL.md` queries `--status all` and re-narrows with the two liveness conjuncts Section 2 already applies (non-terminal, non-draft), so widening the scope does not start reporting stale gates on closed cards.
  - [x] MECHANICAL: Section 4's prose states that a card may appear there while `status: active`, the way Section 2's prose does — the reader learns the rule on both surfaces that depend on it.
  - [x] EMPIRICAL: re-running the shipped Section 4 command on this repo's deck surfaces all 197 live gated cards, not 192.
  - [x] MECHANICAL: plugin and dogfood skill mirrors re-synced (`scripts/sync_plugin_assets.py`, `scripts/port_skills_to_openclaw.py`) so the five copies of the skill stay identical.
  - [x] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass.
worker: {who: "claude[bot]", where: main}
---

# Standup's "Waiting on you" section drops every card that was claimed before it was parked

## Location

`goc/templates/skills/standup/SKILL.md:88-107` — Section 4. The prose
on lines 90-92 promises:

> Surface **all cards** with `human_gate: decision` or `human_gate:
> session`, oldest first. These are parked cards where the agent hit
> the Andon cord and a human must lower the gate to unblock autonomous
> work.

The command on line 95 delivers something narrower:

```bash
goc --json --status open 2>/dev/null | \
  python3 -c "
import json, sys
cards = json.load(sys.stdin)
waiting = [c for c in cards if c.get('human_gate') in ('decision', 'session')]
```

## What's broken

`--status open` is applied by `filter_cards` *before* the block's own
gate predicate ever sees the data, so a card that was claimed
(`status: active`) and *then* raised its gate is gone before the
filter runs. That is not an edge case — it is the normal shape of an
Andon-cord pull: `Skill(pull-card)` claims a card, works it, discovers
it needs a human judgement, raises the gate, and leaves it parked at
`active`. The cards Section 4 exists to surface are precisely the ones
its query drops.

The same file already settled this. Section 2 carried the identical
scope error and was fixed on 2026-09-16
([standup-impeded-section-omits-active-cards-carrying-a-waiting-overlay](../standup-impeded-section-omits-active-cards-carrying-a-waiting-overlay/));
its prose now states the rule outright:

> A card may appear here even while `status: active` — the overlay is
> orthogonal to the progress status, which is why the Context block
> above queries `--status all` rather than the open queue and then
> drops terminal and draft cards by hand.

`human_gate` is orthogonal to progress status for exactly the same
reason `waiting_on` is — both are overlays, neither is a status. Forty
lines later the same skill teaches the principle in one section and
violates it in the next.

The engine agrees with the prose, not the query. The SessionStart hook
(`goc/templates/hooks/deck_session_start.py`) reports these cards under
their own banner in every session this repo opens:

```text
[GoC] Parked active card(s) (awaiting human): list-game-of-cards-on-anthropic-community-marketplace,
parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them,
pattern-check-hook-binary-misses-connect-to-existing-root,
support-external-game-of-cards-state-location,
terminal-status-guard-missing-across-mutation-verbs — agent cannot resume.
```

Standup then tells the human none of those five cards is waiting on
them.

## Empirical evidence

`reproduce.py` runs the shipped Section 4 block over the full
(status x gate) grid:

```text
card               status     gate      draft  expected  reported
----------------------------------------------------------------------
open-decision      open       decision  False  True      True
open-session       open       session   False  True      True
active-decision    active     decision  False  True      False   <-- WRONG
active-session     active     session   False  True      False   <-- WRONG
active-ungated     active     none      False  False     False
open-ungated       open       none      False  False     False
done-stale-gate    done       decision  False  False     False
draft-decision     open       decision  True   False     False

DEFECT: 2 card(s) misreported: active-decision, active-session
```

On this repo's own deck the loss is 5 cards out of 197 live gated
cards — 192 reported:

```text
=== standup Section 4 as written ===
192 cards surfaced
=== truth: every live card at a gate ===
197 live gated cards
MISSED by Section 4: 5
   support-external-game-of-cards-state-location | active | session
   list-game-of-cards-on-anthropic-community-marketplace | active | decision
   parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them | active | decision
   pattern-check-hook-binary-misses-connect-to-existing-root | active | session
   terminal-status-guard-missing-across-mutation-verbs | active | decision
```

## Why it matters

The five hidden cards are the *most* expensive ones to hide. A card at
`open` + `decision` was gated at filing time by an agent that never
started it; a card at `active` + `decision` was gated by an agent that
already spent a session on it, loaded the context, and stopped one
judgement call short of finishing. Those are the highest-leverage
decisions a human can make, and standup — the one read designed to put
decisions in front of a human — is silent about them.

The loss compounds with the deck's shape. `goc --ready` is empty today
and Section 5's own prose says "an empty pull queue is the day's
headline, and Section 4 is its cause." When Section 4 under-reports its
cause, the headline has no explanation attached.

`goc triage` is not a workaround: it carries the same defect, tracked
as [parked-active-cards-are-missing-from-goc-triage](../parked-active-cards-are-missing-from-goc-triage/),
so delegating Section 4 to `goc triage --json` would inherit the bug
rather than retire it.

## The family — a caller no shared predicate can reach

This is the 5th consumer of the missing claimed-vs-parked distinction
catalogued on
[active-state-conflates-being-worked-on-with-parked-at-human-gate](../active-state-conflates-being-worked-on-with-parked-at-human-gate/),
which is the architectural card for the shape and stays the human's
call. It is filed as an instance rather than a 5th point-fix proposal
because it is **not interchangeable with the other four**: every one of
those is a Python call site in `goc/engine.py` or a hook that imports
the engine, so all three options on the root card (`is_parked_active`
helper / derived display state / status enum split) retire them by
construction. This one is a shell pipeline inside a markdown skill
body, executed on a host with no installed package and no import path.
No helper shape reaches it — the only fix available is to widen the
query the skill ships.

That is the same argument recorded three days earlier for standup
Section 2 on
[waiting-impedes-callers-reimplement-the-terminal-status-liveness-gate-and-drift](../waiting-impedes-callers-reimplement-the-terminal-status-liveness-gate-and-drift/),
and it lands the same way: fix the instance now, wire it to the root,
leave the architecture to the human.

## Fix (applied)

`goc/templates/skills/standup/SKILL.md:88-119` — Section 4 now spans
every live status and re-narrows by hand, the shape Section 2 already
ships:

- the query is `--json --status all`, not `--status open`;
- the existing gate predicate is untouched;
  `c['status'] not in ('done', 'disproved', 'superseded')` and
  `not c.get('draft')` are added beside it. Both are required by the
  widening, for reasons specific to the gate: closing a card never
  lowers its gate, so a terminal card can carry a stale one, and
  `goc new` gates at `decision` by default, so every unauthored
  scaffold is gated and would otherwise flood the section.

Section 4's prose gained a paragraph naming that scope and the
Andon-cord shape it exists for, so the next reader does not narrow the
query back to the open queue — the same sentence Section 2 carries,
stated for the axis Section 4 reads.

`tests/test_standup_waiting_on_you_block_scope.py` pins it: three
behavioural cases extract the fenced block out of `SKILL.md` and
execute it verbatim against a temp deck covering the (status x gate)
grid, and a fourth asserts the query text is not re-narrowed. Two of
the four fail against the pre-fix template.

### Deliberately out of scope

`goc triage` — the engine's own version of this view — still carries
the identical narrowing, tracked as
[parked-active-cards-are-missing-from-goc-triage](../parked-active-cards-are-missing-from-goc-triage/)
at gate `decision`. Section 4 is left as its own pipeline rather than
delegated to `goc triage --json`, because delegating today would
inherit that defect; once the root card is decided, collapsing the two
is the natural follow-up.

## Artifacts

- `reproduce.py` — runs the shipped Section 4 block over the full
  (status x gate) grid; exits 1 against the pre-fix template, 0 after.

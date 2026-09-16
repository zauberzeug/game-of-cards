---
title: standup-impeded-section-omits-active-cards-carrying-a-waiting-overlay
summary: "The standup skill's Impeded Context block queries `goc --json --status open`, so an `active` card carrying a live `waiting_on` overlay is dropped before the filter runs — contradicting the skill's own Section 2 prose, which states a card may appear there even while `status: active`. The engine settled this exact scope question for `goc --waiting` in the closed card goc-waiting-default-status-hides-active-impeded-cards; the skill body never got the equivalent update, and it hides one real card on this repo's deck today."
status: active
stage: null
contribution: medium
created: "2026-09-16T04:55:39Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, documentation]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits 1 on today's tree and 0 after the fix — the engine-impedes/standup-omits set is empty, and the terminal `c-done-impeded` cell stays out of the reported set so widening the scope does not start reporting closed cards.
  - [ ] TDD: a regression test under `tests/` asserts the Section 2 Context block's query is not status-narrowed past the liveness scope `live_impeded` defines, and fails on today's template.
  - [ ] MECHANICAL: `goc/templates/skills/standup/SKILL.md` Section 2 Context block updated at the source of truth; mirrors resynced via `pre-commit run --all-files` and the OpenClaw port re-run, with `python3 scripts/port_skills_to_openclaw.py --check` clean.
  - [ ] MECHANICAL: the `waiting_on`-truthiness predicate is left untouched — the four-cell matrix belongs to the parked sibling `standup-impeded-filter-drifts-from-engine-on-elapsed-and-bare-waits`, and this card must not close it by side effect.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` green and `uv run goc validate` clean.
worker: {who: "claude[bot]", where: main}
---

# Standup's Impeded section omits active cards carrying a waiting overlay

## Location

- `goc/templates/skills/standup/SKILL.md:22` — the live `!`-block that
  feeds Section 2.
- `goc/templates/skills/standup/SKILL.md:43-50` — the Section 2 prose it
  is supposed to feed.
- `goc/engine.py:4255-4263` (`_cmd_default`'s default-status branch) and
  `goc/engine.py:2745-2776` (`live_impeded`) — the engine's own answer to
  the same question.

## What's broken

Section 2 of the standup skill states its contract in the body:

> For each card carrying a `waiting_on` overlay (shown above): report
> title, the `waiting_on` reason, the `waiting_until` date if any [...]
> **A card may appear here even while `status: active` — the overlay is
> orthogonal to the progress status.**

The Context block that produces "shown above" cannot honour that. It
queries the open queue:

```
!`... sh $b --json --status open; else goc --json --status open; fi ... | python3 -c "
    ... impeded=[c for c in cards if c.get('waiting_on')] ..."`
```

`filter_cards` applies `--status open` *before* the block's `waiting_on`
filter ever runs, so every `active` card is gone by then. The one case
the prose singles out is the one case the query makes unreachable.

This is not an open question about what the right scope is — the engine
already answered it for its own impediment view. `_cmd_default`
auto-extends the default status to `all` when `--waiting` is set:

```python
status = (
    "all"
    if (
        closed_since_threshold is not None
        or getattr(args, "waiting", False)
        or args.board
    )
    else "open"
)
```

with the comment `--waiting and --closed-since both surface cards beyond
the open queue (active-impeded cards, closed cards)`. That widening was
the whole content of
[goc-waiting-default-status-hides-active-impeded-cards](../goc-waiting-default-status-hides-active-impeded-cards/)
(closed 2026-06-21). `live_impeded` then re-narrows the widened set by
its two liveness conjuncts — non-terminal status, not a draft — because
"closing never clears `waiting_on` / `waiting_until`".

The skill body never got the equivalent update, so it still carries the
pre-fix scope three months later.

## Empirical evidence

`reproduce.py` builds a four-cell deck and runs the Context block
verbatim — read out of `SKILL.md` rather than restated, so it cannot
pass against a stale copy of the query — against `goc --waiting --json`:

```
standup Section 2 Context block : ['b-open-impeded']
engine `goc --waiting` (truth)  : ['a-active-impeded', 'b-open-impeded']

engine impedes, standup omits  : ['a-active-impeded']
standup reports, engine does not: []

DEFECT PRESENT — standup Section 2 disagrees with the engine.
```

It also fires on this repo's own deck, unmodified, today. The Context
block reports three impeded cards; `goc --waiting` reports four. The
missing one is `openclaw-plugin-skills-force-repeated-reads-every-session`
(`status: active`, `waiting_on: external`) — the same card the
SessionStart hook announces on every session as
`[GoC] Impeded active card(s) (waiting_on): ...`.

## Why it matters

Standup is the daily "what's stuck" read, and Section 2 is the section a
human uses to decide whether an impediment needs chasing. An active card
is the *most* expensive one to lose there: it is claimed, so nothing else
will pull it, and it is impeded, so its own worker cannot advance it.
Silently omitting it means the card can sit blocked indefinitely while
every standup reports a clean impediment list.

Two other surfaces already report that card correctly — the SessionStart
hook and `goc --waiting` — so the skill is the only one of the three that
lies, and it is the one presented to the human as the daily summary.

Reachability: a user invokes `Skill(standup)` (auto-invoke on "what's
up", "what's stuck", "daily check"). The Context block runs at skill-load
time and the agent reports its output verbatim as Section 2. No
hand-editing or unusual card shape is required — any deck with an active
card carrying an overlay reproduces it.

## Fix

In `goc/templates/skills/standup/SKILL.md:22`, widen the query to the
scope `live_impeded` defines and re-narrow it with the same two liveness
conjuncts the engine applies:

- query `--status all --json` instead of `--json --status open` (matching
  `_cmd_default`'s `--waiting` widening);
- keep the existing `c.get('waiting_on')` predicate untouched, and add
  `c['status'] not in ('done', 'disproved', 'superseded')` and
  `not c.get('draft')` — `live_impeded`'s two liveness clauses, needed
  because `--status all` admits both terminal cards (whose overlay is
  never cleared on close) and unauthored draft scaffolds.

### Deliberately out of scope

The `c.get('waiting_on')` truthiness test is *also* wrong — it drifts
from `waiting_impedes` across the four-cell `waiting_on` x
`waiting_until` matrix. That is a separate, already-filed,
decision-gated defect:
[standup-impeded-filter-drifts-from-engine-on-elapsed-and-bare-waits](../standup-impeded-filter-drifts-from-engine-on-elapsed-and-bare-waits/).
Its "Possible fixes" section proposes replacing the whole block with
`goc --waiting --json`, which would fix this card's scope defect for
free — and treats the scope itself as an undecided knob ("add
`--status open` if this section should stay open-only"). Section 2's own
prose already answers that: it must not stay open-only.

So the two cards compose but must not be merged. This one fixes the
scope, which is determined; that one picks the predicate mechanism,
which is a human call. A fix here that reaches for `--waiting` would
close a parked card without its decision, so it deliberately does not.

## Artifacts

- `reproduce.py` — the four-cell comparison above.

---
title: standup-impeded-filter-drifts-from-engine-on-elapsed-and-bare-waits
summary: "The `standup` skill's Context block filters impeded cards with `[c for c in cards if c.get('waiting_on')]`. The engine's `waiting_impedes` predicate evaluates a four-cell matrix over `waiting_on` x `waiting_until`. The skill drifts from the engine in two cells: (1) `waiting_on` set with elapsed `waiting_until` is engine-NOT-impeded (the card has re-entered the queue) but the skill still lists it as impeded; (2) a bare future `waiting_until` (no reason) is engine-IMPEDED (deferred wait) but the skill omits it. Same drift class as the recent session-start `_is_impeded` precision fix — a hook re-implementing the engine predicate from one of its two inputs."
status: open
stage: null
contribution: low
created: "2026-05-29T11:27:22Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, documentation]
definition_of_done: |
  - [ ] EMPIRICAL: Standup Context block's impeded filter agrees with the engine's `waiting_impedes` / `card_is_ready` across the four-cell `waiting_on` x `waiting_until` matrix, including the bare-deferral case (`waiting_until` set with no `waiting_on`).
  - [ ] TDD: `reproduce.py` (in this card's directory) exits 0 — false-positive and false-negative sets both empty — and a unittest under `tests/` exercises the same matrix so a future template edit cannot reintroduce the drift silently.
  - [ ] MECHANICAL: Skill source-of-truth at `goc/templates/skills/standup/SKILL.md` updated and `.claude/skills/standup/SKILL.md` resynced (per AGENTS.md "Skill and hook files have two copies" — edit the template, pre-commit sync mirrors).
  - [ ] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green.
---

# Standup impeded filter drifts from the engine on elapsed and bare waits

## Problem

`goc/templates/skills/standup/SKILL.md` line 18 runs this filter to
populate the "Impeded (waiting overlay)" section:

```python
impeded = [c for c in cards if c.get('waiting_on')]
```

The engine's `waiting_impedes` (`goc/engine.py:1752`) evaluates a
four-cell matrix over both overlay fields:

| `waiting_on` | `waiting_until`         | engine: impeded? |
|--------------|-------------------------|------------------|
| set          | absent                  | yes (open-ended) |
| set          | future                  | yes              |
| set          | **elapsed**             | **no** (resurfaces) |
| unset        | future                  | **yes** (deferred) |
| unset        | elapsed                 | no               |
| unset        | absent                  | no               |

The standup filter checks `waiting_on` alone, so it disagrees with the
engine in two cells:

1. `waiting_on` set + elapsed `waiting_until` — the engine has resurfaced
   the card (`card_is_ready` returns True; `goc --board` drops the ⏳;
   `pull-card` will grab it), but standup still lists it under
   "Impeded".
2. Unset `waiting_on` + future `waiting_until` (a bare deferral) — the
   engine treats it as a `deferred` wait and hides it (`card_is_ready`
   returns False; `goc --board` shows ⏳; `pull-card` skips it), but
   standup OMITS it from "Impeded".

## Reproducer

`reproduce.py` builds a temp deck with one card per matrix cell, runs
`goc --json --status open` against it, applies the standup filter
verbatim, and compares to the engine's `ready` field (also exposed in
the JSON record). Output:

```
standup-skill impeded filter      : ['a-elapsed-with-reason', 'c-reason-only']
engine waiting_impedes / not-ready: ['b-future-bare-deferral', 'c-reason-only']

false-positive (skill says impeded, engine has resurfaced): ['a-elapsed-with-reason']
false-negative (engine impedes, skill omits)              : ['b-future-bare-deferral']

DRIFT REPRODUCED
```

## Why it matters

The standup section advertises "what's stuck" — the daily read users
rely on to learn which cards are impeded and which can be pulled. When
the filter drifts from the queue truth, both directions of the lie
hurt:

- A reader sees `a-elapsed-with-reason` in "Impeded" and assumes it's
  parked. Meanwhile `Skill(pull-card)` autonomously pulls it on the
  next /loop tick — the card was never actually parked, the overlay
  has already self-cleared per the engine's elapsed-wait contract.
- A reader does NOT see `b-future-bare-deferral` in "Impeded" and
  assumes nothing is deferred. But the card is hidden from the pull
  queue until 2030, and the human has no signal that work is parked.

This is the **same class** as the recently closed
`session-start-hook-misreads-same-day-datetime-waiting-until-as-not-impeded`
(commit 64361be) — a hook/skill re-implements the engine's impediment
predicate from one of its two inputs and drifts. The engine fixed the
hook by mirroring `_waiting_until_instant`; the standup skill body
never got the equivalent update.

## Reachability path

User invokes `Skill(standup)` (auto-invoke triggers: "what's up",
"what's stuck", "daily check", "morning check"). The skill body's
Context block runs the python one-liner, prints the impeded list, and
the agent reports it verbatim in Section 2 of the output. Any user
following the standup as their canonical "what's parked" view sees the
drift.

## Possible fixes

The cleanest is to delegate to the engine's precomputed signal. The
JSON record already exposes `ready` (`engine.py:2345`,
`card_is_ready`). The filter can be:

```python
impeded = [c for c in cards
           if c.get('human_gate') == 'none'
           and not c.get('ready')
           and (c.get('waiting_on') or c.get('waiting_until'))]
```

The `human_gate == 'none'` clause keeps the impeded section about the
overlay (not the human gate, which has its own Section 4); the `not
ready` clause defers the four-cell matrix to the engine; the
`waiting_on or waiting_until` clause keeps the section about the
overlay specifically, not dependency-readiness (the third leg of the
three-axis model has its own visibility in `--board`).

Alternatively, expose `waiting_impedes` as a precomputed JSON field
alongside `ready` — a one-line addition to `render_json` — and let
the skill check that directly.

Either way, the skill should not be re-deriving the predicate from a
single field when both inputs are already in the JSON payload.

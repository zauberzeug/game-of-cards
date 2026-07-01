---
title: ready-leverage-line-names-draft-scaffolds-as-the-highest-gated-card
summary: "`goc --ready`'s leverage line (`render_leverage_line`) builds its `open_gated` candidate set filtering on status/human_gate/`waiting_impedes` but omits the `card_is_draft` gate that the sibling open-only predicate `card_is_ready` applies. So an unauthored `goc new` scaffold with the default `decision` gate is surfaced to the operator as the 'Highest gated card' being traded off, even though every other surface (queue, board, `--status open`, the pullable set) correctly hides it. Third live instance of the liveness-gate drift the meta-fix umbrella tracks."
status: done
stage: null
contribution: medium
created: "2026-07-01T02:28:00Z"
closed_at: "2026-07-01T02:35:27Z"
human_gate: none
advances:
  - waiting-impedes-callers-reimplement-the-terminal-status-liveness-gate-and-drift
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (the leverage line no longer names a draft scaffold).
  - [x] TDD: a unit/regression test asserts `render_leverage_line` returns `""` when the only open gated card is a draft, and names an authored gated card when one is also present.
  - [x] MECHANICAL: `render_leverage_line`'s `open_gated` comprehension excludes `card_is_draft`, matching `card_is_ready`.
  - [x] PROCESS: `waiting-impedes-callers-reimplement-the-terminal-status-liveness-gate-and-drift` cross-referenced as this instance's umbrella (advances edge wired).
  - [x] PROCESS: `uv run goc validate` clean; full regression suite green.
worker: {who: "claude[bot]", where: main}
---

# `goc --ready` leverage line names draft scaffolds as the highest gated card

## Location

`goc/engine.py:3227-3232` — the `open_gated` comprehension inside
`render_leverage_line`.

## What's broken

The leverage line printed after a `goc --ready` pick compares the pulled
card against the "Highest gated card" — the top open card sitting behind a
`decision` / `session` gate. Its candidate set omits the draft gate:

```python
open_gated = [
    t for t in all_cards
    if t.status == "open"
    and t.human_gate in ("decision", "session")
    and not waiting_impedes(t)
]
```

Every other queue/scheduler surface excludes unauthored `draft: true`
scaffolds through the shared `card_is_draft` predicate. The sibling
*open-only* predicate `card_is_ready` (`engine.py:2337-2364`) does exactly
that:

```python
def card_is_ready(card, by_title):
    if card.status != "open":
        return False
    if card_is_draft(card):        # <-- the gate render_leverage_line omits
        return False
    if card.human_gate != "none":
        return False
    if waiting_impedes(card):
        return False
    return True
```

`card_is_draft`'s own docstring names it "the single 'not yet real'
predicate consulted by … the queue / scheduler / board / json surfaces —
so the rule is defined once and cannot drift per call site." The leverage
line is the one open-only surface that drifted from it.

## Empirical evidence

`reproduce.py` builds a temp deck with one authored ready card
(`real-ready`, gate none) and one freshly-filed draft scaffold
(`phantom-draft`, default gate `decision`):

```
=== goc --ready ===
TITLE       STATUS  CONTR.  VALUE  GATE  TAGS  DOD
----------  ------  ------  -----  ----  ----  ---
real-ready  open    low       1.0  none        0/1
Pulling real-ready (value 1.0). Highest gated card: phantom-draft (value 9.0, gate decision).

leverage line names the draft scaffold : True

FAIL: the leverage line names `phantom-draft`, an unauthored draft
scaffold, as the Highest gated card. No real gated card exists, so the
clause should be omitted entirely.
```

`phantom-draft` appears in no other view — `goc --board`, `goc --status
open`, and `--ready`'s own pullable table all correctly exclude it as a
draft. Only this line leaked it.

After the fix, the same deck omits the clause entirely (no real gated card
exists), and `reproduce.py` exits 0:

```
=== leverage line ===
(no leverage line)

leverage line names the draft scaffold : False

OK: the leverage line excludes draft scaffolds (no real gated card -> clause omitted).
```

## Why it matters

The leverage line is the pull-card skill's ping-the-human signal: when the
gated card's value is ≥3× the pulled card's, the autonomous puller is told
to ask the human to lower the gate before draining low-value work. A draft
scaffold — which `goc new` stamps at `contribution: high` / `value 9.0` by
default and which no human has authored, let alone gated — inflates that
comparison and can trigger a spurious "ping the human to lower the gate"
recommendation for a card that isn't real work.

**Reachability:** `goc new <title> --contribution high` (the default gate is
`decision`) produces exactly this input; the scaffold sits in the deck
until published/claimed/discarded. Any `goc --ready` run while such a draft
exists surfaces it in the leverage line.

## Fix

Add the draft exclusion to the comprehension so it matches `card_is_ready`:

```python
open_gated = [
    t for t in all_cards
    if t.status == "open"
    and not card_is_draft(t)
    and t.human_gate in ("decision", "session")
    and not waiting_impedes(t)
]
```

## Relationship

This is the third live instance of the drift catalogued by
[waiting-impedes-callers-reimplement-the-terminal-status-liveness-gate-and-drift](../waiting-impedes-callers-reimplement-the-terminal-status-liveness-gate-and-drift/)
— that umbrella's own caller table already lists the gated-leverage line as
an "open-only" variant but does not flag that it, unlike its sibling
`card_is_ready`, omits the `card_is_draft` exclusion. The point-fix here
mirrors the closed
[waiting-filter-surfaces-draft-scaffolds-as-active-impediments](../waiting-filter-surfaces-draft-scaffolds-as-active-impediments/);
the eventual centralized live/open-only helper (the umbrella's decision)
subsumes both.

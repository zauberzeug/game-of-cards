---
title: active-state-conflates-being-worked-on-with-parked-at-human-gate
summary: "`status: active` covers two lifecycle states the rest of the system treats differently: cards an agent currently has under work (`human_gate: none`) and cards that were claimed and then parked behind a raised gate awaiting a human (`human_gate: decision|session`). Every consumer that filters or labels active cards re-derives the distinction by hand — three siblings (`session-start-hook-shows-gated-active-cards-as-resumable` closed, `parked-active-cards-are-missing-from-goc-triage` open, `parked-active-cards-are-missing-from-goc-ready-leverage-line` open) plus this 4th surface (`render_active_notice` at `goc/engine.py:2480-2499`, which mislabels parked-active cards as `claimed` and tells readers to check `before claiming new work`). Per audit-deck Phase 3 sibling-sweep rule, four instances of the same root-cause shape triggers the architectural meta-fix instead of a 4th point-fix."
status: open
stage: null
contribution: medium
created: "2026-05-30T11:39:59Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - session-start-hook-shows-gated-active-cards-as-resumable
  - parked-active-cards-are-missing-from-goc-triage
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] PROCESS: pick the architectural shape from `## Decision required` and record the choice via `Skill(decide-card)` (lowers the gate to `none`). The pick determines DoD items below.
  - [ ] MECHANICAL: a shared predicate (`is_parked_active(card)` or equivalent) lands in `goc/engine.py` and is used by all four consumers — `render_active_notice`, `_cmd_triage`, `render_leverage_line`, and `deck_session_start.py` — so adding a fifth view does not require re-deriving the distinction.
  - [ ] MECHANICAL: `render_active_notice` (`goc/engine.py:2480-2499`) emits two separate framings: claimed-active cards keep the `before claiming new work` advice; parked-active cards are labeled `parked (awaiting human)` and direct readers to `goc triage` instead.
  - [ ] MECHANICAL: the existing sibling cards (`parked-active-cards-are-missing-from-goc-triage`, `parked-active-cards-are-missing-from-goc-ready-leverage-line`) are either subsumed by this meta-fix (closed with a forward pointer here) or fixed in the same PR; the choice is recorded in `log.md`.
  - [ ] TDD: a regression test exercises `render_active_notice` against a fixture deck containing (a) `status: active` + `human_gate: none`, (b) `status: active` + `human_gate: decision`, (c) `status: active` + `human_gate: session`. The test asserts that (b) and (c) appear in a parked-framing bucket, not lumped under `claimed`.
  - [ ] EMPIRICAL: re-running `goc --ready` on this repo's current deck (which carries 2 parked-active cards on 2026-05-30) emits a message that names the cards as parked (awaiting human), not as `claimed cards … before claiming new work`.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass.
---

# `status: active` conflates being-worked-on with parked-at-human-gate

## Location

`goc/engine.py:2480-2499` (`render_active_notice`) is the 4th surface
to derive this distinction by hand. The selection filter on line 2489
is:

```python
active = sort_default([t for t in cards if t.status == "active"], values=values)
```

The rendered message on lines 2496-2498 is:

```python
return (
    f"ACTIVE: {len(active)} claimed {noun} outside this open queue: {shown}. "
    "Check `goc --status active` or `goc --board` before claiming new work."
)
```

## What's broken

`status: active` is a single status enum value, but agents who consume
queue views treat two sub-states differently:

| sub-state | shape | what the agent should do |
| --- | --- | --- |
| **claimed-active** | `status: active`, `human_gate: none` | another agent is working it; pick something else |
| **parked-active** | `status: active`, `human_gate: decision\|session` | claimed *and then* parked; agent cannot resume — a human must lower the gate first |

`render_active_notice` collapses both into one bucket and tags every
listed card as `claimed`, with the trailing advice `before claiming
new work`. That framing tells a pull-card reader the listed cards are
in someone's workspace — when, in this repo today, both listed cards
are parked at human gates and the SessionStart hook has already told
the same agent they cannot be resumed.

The SessionStart hook (`goc/templates/hooks/deck_session_start.py`)
was fixed for this exact conflation by the closed predecessor
[session-start-hook-shows-gated-active-cards-as-resumable](../session-start-hook-shows-gated-active-cards-as-resumable/)
— it now emits:

> `[GoC] Parked active card(s) (awaiting human): <titles> — agent cannot resume.`

But `render_active_notice` still emits the old framing on the same
cards a few lines later. The two messages contradict each other in
the same session.

## Empirical evidence (current repo state, 2026-05-30)

```text
$ uv run goc --ready
ACTIVE: 2 claimed cards outside this open queue: support-external-game-of-cards-state-location, list-game-of-cards-on-anthropic-community-marketplace. Check `goc --status active` or `goc --board` before claiming new work.
```

Both listed cards have `human_gate` raised (`session` and `decision`
respectively) and are awaiting human input. Neither is "claimed" in
the sense of "another agent is working it." The same session's
SessionStart hook output reads:

```text
[GoC] Parked active card(s) (awaiting human): list-game-of-cards-on-anthropic-community-marketplace, support-external-game-of-cards-state-location — agent cannot resume.
```

Two surfaces in the same engine, same cards, contradictory framings.

## Reachability path

`render_active_notice` runs on every invocation of `goc`,
`goc --ready`, `goc --status open`, `goc --tag …`, and any other
filtered list view (the open-queue formatter calls it unconditionally
before the table). A pull-card / next-card session reads its output
on every wake. The conflation is observed end-to-end in this very
session's tool transcripts — the warning printed during the audit
run that filed this card.

## The family — 4th sibling in a catalogued root-cause cluster

Per `Skill(audit-deck)` Phase 3 step 5 ("sibling sweep after
confirmation"): when the same root-cause shape produces a 4th
instance, the response is the architectural meta-fix, not another
point-fix. The family:

1. [session-start-hook-shows-gated-active-cards-as-resumable](../session-start-hook-shows-gated-active-cards-as-resumable/)
   (closed 2026-05-29) — the SessionStart hook fix that introduced
   the `Parked active card(s) (awaiting human)` framing.
2. [parked-active-cards-are-missing-from-goc-triage](../parked-active-cards-are-missing-from-goc-triage/)
   (open, gate decision) — `_cmd_triage` filters by
   `status == "open"`, silently EXCLUDING parked-active cards from
   the very view designed to surface them.
3. [parked-active-cards-are-missing-from-goc-ready-leverage-line](../parked-active-cards-are-missing-from-goc-ready-leverage-line/)
   (open, gate decision) — `render_leverage_line` filters the
   gated-comparison pool by `status == "open"`, under-reporting the
   Andon-cord signal.
4. **This card** — `render_active_notice` INCLUDES parked-active
   cards but mislabels them with `claimed` framing.

Each instance is one consumer of the same missing predicate. The
fix is a shared helper that distinguishes claimed-active from
parked-active, applied to all four consumers (and the next one a
reader adds).

## Decision required

Three credible architectural shapes, listed in increasing order of
invasiveness:

### Option A — Shared predicate, no schema change

Introduce a module-level helper in `goc/engine.py`:

```python
def is_parked_active(card: Card) -> bool:
    return card.status == "active" and card.human_gate in ("decision", "session")
```

Update all four consumers to call it; relabel `render_active_notice`
output to split claimed from parked. Keeps `status: active` as a
single enum value; the parked/claimed distinction is derived at read
time from `(status, human_gate)`. Minimal schema churn; the existing
two open siblings collapse into "update consumer N".

### Option B — Add `parked-active` as a derived display state

Same helper as A, but additionally surface `parked-active` as a
distinct **rendered** state in board / table views (the `STATUS`
column would show `active` vs `parked`, even though the underlying
frontmatter stays unchanged). More visible to humans reading the
board; requires updating the board renderer and column-width
machinery.

### Option C — Split `active` into two status enum values

Make `parked-active` a first-class `status:` value alongside
`active`. The lifecycle becomes
`open → active → (parked-active ↔ active) → done|disproved|superseded`.
Every status-flip site (`goc status`, `goc done`, `goc decide`, the
attestation pipeline, validation) gets new transitions. Highest
invasiveness; requires a migration of existing parked cards.

### Recommendation

Option A. The two open siblings are already pending a fix-shape
decision; A is the smallest delta that gives all four consumers one
predicate to depend on. B and C are reachable from A — once the
helper exists, promoting it to a column header or a status enum
value is a follow-up.

## Fix sketch (under Option A)

1. Add `is_parked_active` to `goc/engine.py` near `waiting_impedes`
   (same family of derived-state predicates).
2. `render_active_notice` (lines 2480-2499): split `active` into
   `claimed` and `parked` lists. Emit one line per non-empty list:

   ```text
   ACTIVE (claimed by an agent): <n> card(s) outside this open queue: <titles>. Check `goc --status active` before claiming new work.
   PARKED (awaiting human): <n> card(s) outside this open queue: <titles>. See `goc triage` for the full list.
   ```

3. `_cmd_triage` (`goc/engine.py:~4609-4671`): widen the filter to
   `status in ("open", "active") and human_gate != "none"`. Either
   group both buckets together (current header reads "Waiting on
   you") or label parked-active rows separately.
4. `render_leverage_line` (`goc/engine.py:2443-2477`): same widening
   on the `open_gated` filter.
5. `deck_session_start.py` (and its three auto-synced mirrors): keep
   the existing framing — it's already correct — but switch to the
   new `is_parked_active` helper for consistency.

## Why it matters

Every autonomous pull-card session reads `render_active_notice`'s
output before deciding whether to claim. The current message says
"these are claimed" when they are actually "parked at a human gate
that the puller cannot lower." That confusion biases the puller
toward filing an audit-deck card (this exact path) or invoking
`Skill(decide-card)`-class follow-ups when, in reality, the only
correct action is to skip those cards. Multiply by every /loop /
schedule wake and the misframing burns autonomous capacity on phantom
work.

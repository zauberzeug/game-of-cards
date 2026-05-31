---
title: scheduler-descendant-prune-duplicates-card-is-ready-axes-across-two-sites
summary: "`compute_values.value_for` (`engine.py:2083`) and `sort_default.live_direct` (`engine.py:2314`) each independently maintain a descendant-prune predicate that mirrors `card_is_ready`'s gates minus the `status == \"open\"` clause. Three sibling cards have now extended both sites in lockstep — terminal axis, impediment axis, human-gate axis. A fourth axis added to `card_is_ready` would silently leak through both prunes again. Extract a shared `card_is_workable_for_scheduler(card)` helper (or equivalent) so the live-AND-workable rule is defined once and the two sites cannot drift."
status: active
stage: null
contribution: medium
created: "2026-05-31T02:16:18Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [meta-fix, api-contract]
definition_of_done: |
  - [ ] MECHANICAL: introduce a single predicate (helper function or named expression) that captures the "live-AND-workable scheduler descendant" rule — exactly `card_is_ready` minus the `status == "open"` clause, equivalently: not terminal AND not `waiting_impedes` AND `human_gate == "none"`. Both `value_for` (in `compute_values`) and `sort_default.live_direct` consult it; the conditional bodies of the two `continue` blocks contain no axis enumeration of their own.
  - [ ] MECHANICAL: the helper lives next to `card_is_ready` (`engine.py:1913-1933`) so the two predicates read as a pair — `card_is_ready` for the queue axis, the new helper for the scheduler axis — and a reader updating one immediately sees the other.
  - [ ] TDD: a unit test asserts the predicate-coupling invariant — for every `human_gate ∈ {none, decision, session}`, every `waiting_on ∈ {None, external, resource, deferred}`, and every `status ∈ {open, active, done, disproved, superseded}`, the new helper agrees with `card_is_ready` except when `status == "active"` (where the helper accepts and `card_is_ready` rejects). The test fails if a future axis is added to `card_is_ready` without being mirrored.
  - [ ] TDD: the three existing reproduce.py scripts (`compute-values-inherits-value-through-done-and-superseded-descendants`, `compute-values-amplifies-priority-through-impeded-descendants`, `compute-values-amplifies-priority-through-human-gate-parked-descendants`) still exit 0 — the helper preserves the three closed siblings' behavior verbatim.
  - [ ] MECHANICAL: plugin mirrors synced and `uv run goc validate` clean; full `uv run python -m unittest discover -s tests` clean.
worker: {who: "claude[bot]", where: main}
---

# Scheduler descendant prune duplicates `card_is_ready` axes across two sites

## Location

- `goc/engine.py:2083` — `value_for` (the inner recursion of
  `compute_values`); the descendant-prune `if` block that decides
  whether to walk into a given `advances` target.
- `goc/engine.py:2314` — `sort_default.live_direct`; the live-edge
  tiebreak counter that ranks two equal-value cards by how many
  "workable" direct descendants each carries.
- `goc/engine.py:1913-1933` — `card_is_ready`, the queue-visibility
  predicate the two prune sites are trying to mirror (minus its
  `status == "open"` clause).

## What's duplicated

Both prune sites independently enumerate the same axis set:

```python
# engine.py:2083 (value_for, inside compute_values)
if (
    dest_card.status in TERMINAL_STATUSES
    or waiting_impedes(dest_card)
    or dest_card.human_gate != "none"
):
    # ... scheduler axis is live-AND-workable only ...
    continue

# engine.py:2314 (sort_default.live_direct)
if (
    dc.status in TERMINAL_STATUSES
    or waiting_impedes(dc)
    or dc.human_gate != "none"
):
    continue
```

That set is `card_is_ready`'s three rejection axes minus the
`status == "open"` clause — `active` descendants stay workable for the
scheduler axis while being ineligible for the queue:

```python
# engine.py:1913-1933 (card_is_ready)
def card_is_ready(card: Card, by_title: dict[str, Card]) -> bool:
    if card.status != "open":      return False     # ← scheduler ALLOWS active
    if card.human_gate != "none":  return False     # ← scheduler MIRRORS
    if waiting_impedes(card):      return False     # ← scheduler MIRRORS
    return True
```

## The drift history that motivates extraction

The two prune sites have been extended in lockstep three times,
each as its own card with its own commit and its own `reproduce.py`:

1. [compute-values-inherits-value-through-done-and-superseded-descendants](../compute-values-inherits-value-through-done-and-superseded-descendants/)
   (done) — added the `status in TERMINAL_STATUSES` axis.
2. [compute-values-amplifies-priority-through-impeded-descendants](../compute-values-amplifies-priority-through-impeded-descendants/)
   (done) — added the `waiting_impedes` axis.
3. [compute-values-amplifies-priority-through-human-gate-parked-descendants](../compute-values-amplifies-priority-through-human-gate-parked-descendants/)
   (done) — added the `human_gate != "none"` axis.

Each closure rediscovered the *other* site by hand from the card body
or by grep, and each commit duplicated the same logical predicate
twice. A fourth axis added to `card_is_ready` (a hypothetical fifth
`status`, a new gate kind, a second-overlay field) would silently
leak through both prunes again — there is no machine-enforced
coupling between the queue predicate and the scheduler predicate, so
the drift is invisible until a future bug report reconstructs it from
read-path symptoms.

## Reachability

This card does not change observable behavior on any current input —
the three siblings already eliminated every known leak. The risk it
addresses is **future drift**: the next axis added to `card_is_ready`
must also be added to both prune sites, and nothing today fails loudly
if the coupling is missed.

Every read path that ranks the open queue still depends on the
scheduler-axis prune being correct:

- `goc` / `goc --ready` — headline list `pull-card` / autonomous `/loop`
  consult to pick the next card.
- `goc --board` — kanban renderer.
- `Skill(next-card)` — contribution-comparison recommendation.
- `render_leverage_line` (`goc/engine.py:2434`) — the
  `Pulling … (value N). Highest gated card: … (value M, …)` Andon
  advisory.

A drifted prune produces inflated values silently; the symptom
appears as "wrong card pulled" three weeks later. The unit test in
the DoD makes a fourth-axis addition fail-loud at the source.

## Why it matters

The `meta-fix` family rule (audit-deck "sibling sweep") triggers at
N=3 instances of one shape: file one architectural card, don't file a
fourth instance of the same fix. The three siblings above are that
shape. The fix is a one-line helper plus a coupling test — small
enough to land in one session — and removes the entire family from
the deck's future cost.

It also serves as the *design-doc* anchor for the live-AND-workable
rule. The rule is currently stated in three places — the docstring of
`compute_values`, the docstring of `sort_default`, and three sibling
log entries — each phrased slightly differently. A named helper
`card_is_workable_for_scheduler` (or whatever name survives review)
is the canonical source of truth a future reader greps for.

## Fix proposal

The mechanical shape — the design call left to the implementer is
whether to introduce a top-level helper or fold the logic into an
augmented `card_is_ready` that takes a mode flag. The helper is
clearer; the mode-flag form keeps the predicate count at one. Either
satisfies the DoD.

Helper form:

```python
def card_is_workable_for_scheduler(card: Card) -> bool:
    """True iff a descendant may amplify an ancestor's GRPW value.

    Mirrors `card_is_ready` for the scheduler axis: `card_is_ready`
    minus the `status == "open"` clause. `active` descendants stay
    workable because the scheduler walks live work, not just queueable
    work.

    A future axis added to `card_is_ready` must be added here in the
    same edit; `tests/test_scheduler_workable_predicate_coupling.py`
    enforces this invariant.
    """
    if card.status in TERMINAL_STATUSES:
        return False
    if card.human_gate != "none":
        return False
    if waiting_impedes(card):
        return False
    return True
```

Then both sites become:

```python
# value_for
if not card_is_workable_for_scheduler(dest_card):
    continue

# sort_default.live_direct
if not card_is_workable_for_scheduler(dc):
    continue
```

The TDD coupling test (DoD item 3) introspects both predicates
across the full cross-product of `status × human_gate × waiting_on`
states and asserts agreement modulo the `active`-allowed clause.

## Cross-references

- [compute-values-inherits-value-through-done-and-superseded-descendants](../compute-values-inherits-value-through-done-and-superseded-descendants/) (done, terminal axis).
- [compute-values-amplifies-priority-through-impeded-descendants](../compute-values-amplifies-priority-through-impeded-descendants/) (done, impediment axis).
- [compute-values-amplifies-priority-through-human-gate-parked-descendants](../compute-values-amplifies-priority-through-human-gate-parked-descendants/) (done, human-gate axis).

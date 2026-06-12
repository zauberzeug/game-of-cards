---
title: repair-edges-apply-writes-superseded-by-onto-non-superseded-cards
summary: "`goc repair-edges --apply` gates each repair only on cycle detection, so a `supersedes` half-edge whose endpoint is not `status: superseded` gets \"repaired\" by writing `superseded_by` onto an open card — a state `goc validate` rejects with a NEW gating error no verb can fix. The verb prints `Repaired 1 half-edge(s).` and exits 0 while the deck stays red."
status: open
stage: null
contribution: medium
created: "2026-06-12T05:19:44Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] PROCESS: disposition for validator-inconsistent supersession half-edges decided and recorded (see Decision required).
  - [ ] TDD: reproduce.py exits zero (the half-edge is routed to structural review, the open endpoint is left unmutated, and exit is non-zero — or per the chosen disposition).
  - [ ] TDD: regression test — a legitimate supersession half-edge (holder `status: superseded`) still repairs to a validator-clean pair.
  - [ ] TDD: regression test — post-repair deck passes `goc validate` supersession checks whenever `repair-edges --apply` reports success.
---

# repair-edges-apply-writes-superseded-by-onto-non-superseded-cards

## Location

- `goc/engine.py:4699-4719` — `_repair_edge_cycle_problem`, the ONLY structural gate the apply loop consults
- `goc/engine.py:4762-4776` — the apply loop that mutates the inverse side
- `goc/engine.py:1448-1453` — the validator rule the repair output violates (`superseded_by: non-empty requires status: superseded`)
- `goc/engine.py` `validate_supersedes_targets` — the rule proving the *forward* half was already invalid before the repair

## What's broken

The apply loop checks each half-edge for exactly one structural
problem — cycles:

```python
        problem = _repair_edge_cycle_problem(edge, current_cards)
        if problem:
            structural.append((edge, problem))
            continue
        # Apply the missing reverse half: add edge.src to edge.ref's inverse list.
        _mutate_pair(edge.ref, edge.src, edge.inverse, edge.field, add=True)
```

For a half-edge `card-b.supersedes: [card-a]` where `card-a` is
`status: open`, the repair writes `card-a.superseded_by: [card-b]`.
The validator rejects exactly that state as a gating ERROR:

> superseded_by: non-empty requires status: superseded

The forward half was already provably wrong before the repair
(`validate_supersedes_targets`: "supersedes: 'card-a' is not status:
superseded") — so the edge belongs in the verb's existing
"Structural problems requiring human review" bucket, not in the
fixable set. Instead the verb mutates a card it had no business
touching, prints `Repaired 1 half-edge(s).`, and exits 0; the deck
goes from one validator error to two, and the new one
(`superseded_by` on an open card) has no CLI repair path (see
[validate-flags-card-states-that-no-verb-can-repair](../validate-flags-card-states-that-no-verb-can-repair/),
which holds `repair-edges` up as "the template" — it is also a
producer of such states).

## Empirical evidence

`uv run python .game-of-cards/deck/repair-edges-apply-writes-superseded-by-onto-non-superseded-cards/reproduce.py`
(two-card temp deck, `card-b.supersedes: [card-a]`, both open):

```
repair-edges --apply exit code: 0
  repaired: card-b: supersedes contains 'card-a' but card-a.superseded_by is missing 'card-b' (half-edge)
  Repaired 1 half-edge(s).
FAIL repair-edges claimed success on a supersedes edge whose target is not status: superseded
FAIL card-a (status: open) now carries superseded_by: [card-b]
goc validate exit code after repair: 1
  OK  card-b
  ERROR: card-a: superseded_by: non-empty requires status: superseded (status='open')
  ERROR: card-b: supersedes: 'card-a' is not status: superseded (target.status='open'); a typed supersession pointer requires the replaced card to be marked superseded
FAIL the repair INTRODUCED a validator error the verb cannot fix: 'superseded_by: non-empty requires status: superseded'

3 defect signal(s) — repair traded a half-edge for a validator-rejected state and reported success.
```

## Why it matters

Reachability: a `supersedes` entry pointing at a non-superseded card
is exactly what a hand-authored frontmatter edit, a partially applied
`goc status <old> superseded --by <new>` (interrupted between the two
file writes), or a bot commit that bypassed pre-commit produces.
`goc validate` then says "Run 'goc repair-edges --apply' to fix" for
the half-edge — and following that advice makes the deck *worse*:
the open card now carries a terminal-only field, validate stays red,
and the only way back is a hand edit. The verb's success report
(`exit 0`) also breaks scripted flows that chain
`repair-edges --apply && validate`.

## Decision required

What disposition should `repair-edges --apply` give a supersession
half-edge whose completed pair would still (or newly) violate the
validator's supersession invariants?

1. **Structural bucket (recommended).** Extend the per-edge gate
   beyond cycles: before applying, check the post-repair pair against
   the supersession invariants (`superseded_by` ⇒ holder
   `status: superseded`; `supersedes` target is `superseded`). Any
   violation routes the edge to the existing "Structural problems
   requiring human review" output and the existing `sys.exit(1)`
   path, leaving both cards unmutated. Smallest change; matches the
   verb's stated mandate ("restore symmetry", never re-status cards).
2. **Repair plus status flip.** Complete the edge AND set the
   non-superseded endpoint to `status: superseded` (with `closed_at`,
   log entry, forward pointer). Yields a green deck in one step, but
   silently *closes* a card the user may consider live — far beyond
   the verb's mandate, and wrong whenever the `supersedes` entry
   itself was the typo.
3. **General post-state validation.** After each apply, re-validate
   the two touched cards; on any new error, roll the mutation back
   and reclassify as structural. Catches future invariant additions
   automatically, at the cost of a validate dependency inside the
   repair loop.

Option 1 fixes the observed trap; option 3 is the generalized form if
the family recurs.

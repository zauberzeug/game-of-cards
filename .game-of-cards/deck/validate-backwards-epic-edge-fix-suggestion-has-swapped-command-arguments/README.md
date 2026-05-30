---
title: validate-backwards-epic-edge-fix-suggestion-has-swapped-command-arguments
summary: "`goc validate`'s `BACKWARDS_EPIC_EDGE` advisory tells the user to run `goc unadvance <card> --by <child>` then `goc advance <child> --by <card>` to flip the edge. The arguments are swapped relative to `_cmd_advance`/`_cmd_unadvance` semantics: the suggested unadvance is a silent no-op (the edge being targeted lives on the other pair of fields), and the suggested advance re-adds the same bad edge. A user who follows the warning verbatim ends up with the original backwards edge unchanged."
status: open
stage: null
contribution: medium
created: "2026-05-30T06:20:58Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix, documentation]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — running the swapped suggestion verbatim leaves `card.advances: [child]` unchanged, and running the corrected suggestion removes it.
  - [ ] MECHANICAL: `engine.py:1564-1565` rewritten to read `goc unadvance <child> --by <card>` then `goc advance <card> --by <child>` (arguments un-swapped).
  - [ ] TDD: a unit test in `tests/` asserts the warning text contains the corrected command sequence (so a future re-swap is caught at test time, not at user-time).
  - [ ] PROCESS: `log.md` entry recording the fix and the date.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` passes.
---

# `BACKWARDS_EPIC_EDGE` fix suggestion has swapped `<card>` / `<child>` arguments

## Location

`goc/engine.py:1562-1567` — inside `validate_epic_edge_direction`,
the `else` branch (card is NOT human-gated `decision`).

The verbatim string emitted by `goc validate`:

```text
if closure waits on the work, flip to `child.advances:[card]`
(`goc unadvance <card> --by <child>` then `goc advance <child>
--by <card>`); if card closes on its own deliverable, drop the
edge and use a shared tag
```

## What's broken

Starting state of a backwards aggregation epic is
`card.advances: [child]`, which the bidirectional invariant turns
into `child.advanced_by: [card]`.

`_cmd_advance` / `_cmd_unadvance` semantics
(`engine.py:4391-4423`): `goc advance <title> --by <advancer>` adds
the edge `advancer → title`, i.e. `title.advanced_by += advancer`
and `advancer.advances += title`. `goc unadvance` removes the same
pair.

The warning's two suggested commands, expanded against those
semantics:

1. `goc unadvance <card> --by <child>` removes `card.advanced_by -=
   child` and `child.advances -= card`. **Neither side holds those
   entries** — the bad edge lives in `card.advances` and
   `child.advanced_by`. The call is a silent no-op; the bad edge
   stays.
2. `goc advance <child> --by <card>` adds `child.advanced_by += card`
   and `card.advances += child` — **re-adding the bad edge** (or,
   in the no-op-precursor case, leaving the state identical to
   before the sequence ran).

Net effect of following the verbatim warning: zero state change.
The "backwards aggregation epic" the warning was meant to fix is
still there.

Correct command sequence:

```bash
goc unadvance <child> --by <card>   # removes card.advances:[child]
goc advance   <card>  --by <child>  # adds   child.advances:[card]
```

i.e. the `<card>` / `<child>` labels need to swap inside each command.

## Empirical evidence

`reproduce.py` builds a minimal backwards-epic deck (one `high`
contribution `card-a` with `advances:[child-x, child-y, child-z]`
where all children are `low`), runs the verbatim suggested commands,
and prints the on-disk state before/after.

Verbatim output from `uv run python deck/<title>/reproduce.py`:

```text
=== initial state ===
card-a.advances     = ['child-x', 'child-y', 'child-z']
child-x.advanced_by = ['card-a']

=== goc validate (advisory) ===
WARN BACKWARDS_EPIC_EDGE card-a: ... Fix: if closure waits on the
  work, flip to `child.advances:[card]` (`goc unadvance <card>
  --by <child>` then `goc advance <child> --by <card>`); ...

=== running the suggested commands verbatim ===
$ goc unadvance card-a --by child-x
unadvance: card-a.advanced_by -= child-x; child-x.advances -= card-a

$ goc advance child-x --by card-a
advance: child-x.advanced_by += card-a; card-a.advances += child-x

=== state after suggested commands ===
card-a.advances     = ['child-x', 'child-y', 'child-z']    # UNCHANGED
child-x.advanced_by = ['card-a']                            # UNCHANGED

=== running the CORRECTED commands ===
$ goc unadvance child-x --by card-a
unadvance: child-x.advanced_by -= card-a; card-a.advances -= child-x

$ goc advance card-a --by child-x
advance: card-a.advanced_by += child-x; child-x.advances += card-a

=== state after CORRECTED commands ===
card-a.advances     = ['child-y', 'child-z']                # bad edge removed
card-a.advanced_by  = ['child-x']                           # new edge added
child-x.advances    = ['card-a']                            # new edge added
child-x.advanced_by = []                                    # old edge removed
```

## Why it matters

The reachability path is direct: every user who hits a
backwards-aggregation-epic — exactly the cohort the
`no-guardrail-for-canonical-epic-edge-direction` parent card was
filed to help — gets a `goc validate` advisory whose verbatim fix
recipe does not fix the problem. An LLM agent reading the warning
during an autonomous-pull cycle will run the commands, observe no
state change, and likely either give up or guess differently. A
human reader will spend the time to derive the correct argument
order from the command help, then file a defect like this one.

The advisory is one of two backstops for the inverted-epic shape
(the other being the `card-schema` skill text quoted at filing
time). The backstop ships with a wrong fix command, so it
actively misdirects under exactly the failure mode it was
designed for.

## Decision required

The fix is a one-line text rewrite at `engine.py:1564-1565`. The
gate is `decision` because two test-shape choices are open and a
human pick keeps the meta-fix family coherent:

**Option A — minimal text patch + unit-test assertion.** Edit the
f-string so the literal argument order matches `_cmd_*` semantics:

```python
fix = (
    "if closure waits on the work, flip to `child.advances:[card]` "
    "(`goc unadvance <child> --by <card>` then `goc advance <card> "
    "--by <child>`); if card closes on its own deliverable, drop the "
    "edge and use a shared tag"
)
```

Add a unit test in `tests/test_validate_warnings.py` (new or
existing) that asserts the warning text contains
`goc unadvance <child> --by <card>` and
`goc advance <card> --by <child>`. Cheapest fix; catches a future
re-swap at test time.

**Option B — drive the suggested commands through the real
`_cmd_*` functions in a fixture deck and assert on resulting
state.** Stronger guarantee (the test fails the day the warning's
*meaning* drifts, not just its surface text) but ~30 lines of
fixture scaffolding. Likely a fixture-helper opportunity that
generalizes across the `goc-advance-` / `goc-unadvance-` meta-fix
family.

Both options share the same one-line code change; the difference
is test depth. Recommendation: **Option A** unless a fixture helper
is already being built for one of the sibling cards in the
`unadvance`/`advance` meta-fix family — in which case fold this
defect's test into that helper as a second consumer.

## Sibling sweep

Grepping for similar inverted-argument suggestions in other
validator warning strings: no other instances found (only this
warning suggests an `unadvance`/`advance` sequence in its fix text).

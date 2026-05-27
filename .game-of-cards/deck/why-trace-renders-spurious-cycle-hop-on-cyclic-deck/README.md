---
title: why-trace-renders-spurious-cycle-hop-on-cyclic-deck
summary: "`compute_values` appends a `cycle` sentinel to the WHY path when a descendant re-enters an in-progress node; `_format_why` only special-cases the exact `[cycle]` singleton, so a multi-hop path ending in `cycle` (e.g. `[A, cycle]`) renders a phantom card named `cycle` — `→ A (?) → cycle (?)`. Same class as the just-closed why-trace-renders-spurious-self-hop-on-multi-hop-cards (commit cc2d4ce), which trimmed a trailing `self` sentinel but not `cycle`. Only manifests on a cyclic deck, which goc validate rejects — hence low impact and parked unverified."
status: done
stage: null
contribution: low
created: "2026-05-27T04:04:34Z"
closed_at: 2026-05-27T05:50:50Z
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — a WHY path ending in the `cycle` sentinel no longer renders a phantom `→ cycle (?)` hop (trimmed the same way the `self` sentinel now is).
  - [x] TDD: the `[cycle]` singleton still renders `(cycle)` and valid multi-hop paths are unchanged.
  - [x] PROCESS: confirm-or-disprove recorded in log.md; drop the `unverified` tag once reproduce.py lands.
worker: {who: "claude[bot]", where: main}
---

# WHY trace renders a phantom `→ cycle (?)` hop on a cyclic deck

## Hypothesis (file:line, verbatim)

`goc/engine.py:1816-1817` — on re-entry of an in-progress node, `compute_values`
returns the `cycle` sentinel as a single-element path:

```python
if title in in_progress:
    return (own, ["cycle"])
```

The caller prepends its own dest (engine.py:1848 `best = (d_value, [dest, *d_path])`),
so the path that propagates upward is `[dest, "cycle"]`, `[grandparent, dest, "cycle"]`,
etc. — a multi-hop path whose last element is the `cycle` sentinel.

`goc/engine.py:2036` — `_format_why` only special-cases the exact singleton:

```python
if path == ["cycle"]:
    return "(cycle)"
```

A multi-hop path ending in `cycle` falls through to the generic loop and
renders the sentinel as a real card title with `(?)` (unknown value).

## Empirical evidence (probe, not yet a reproduce.py)

```
>>> engine._format_why(['C','A','cycle'], {})
'→ C (?) → A (?) → cycle (?)'      # phantom card named "cycle"
>>> engine._format_why(['cycle'], {})
'(cycle)'                          # singleton handled correctly
```

`compute_values`'s `["cycle"]` return at line 1817 (re-entry branch) is reachable
only on a cyclic `advances` deck; the cycle detector in `goc validate` rejects
those, so this is display-only cosmetics on a validate-failing deck.

## Resolution (2026-05-27) — CONFIRMED and fixed

`reproduce.py` constructs `cycle`-terminated multi-hop paths and asserts
the rendered WHY string. It exits 1 on the pre-fix engine (`→ C (low) →
A (med) → cycle (?)`) and 0 after the fix. `_format_why` now trims a
trailing `cycle` sentinel like `self`, but appends a ` (cycle)` suffix
so the cycle signal is preserved consistently with the `[cycle]`
singleton's `(cycle)` label: a multi-hop cyclic path renders `→ C (low)
→ A (med) (cycle)` instead of a phantom `→ cycle (?)` card. The
falsification recipe's DISPROVED branch did not apply — the cc2d4ce
`self` trim special-cased only `self`, not both sentinels.

## Why deferred (unverified)

The phantom hop only surfaces on a cyclic deck, which is already a validate
FAIL — the WHY-trace output is a secondary symptom of a deck the user must fix
anyway. Direct sibling of the just-closed
[why-trace-renders-spurious-self-hop-on-multi-hop-cards](../why-trace-renders-spurious-self-hop-on-multi-hop-cards/)
(commit cc2d4ce), which fixed the exact same shape for the `self` sentinel —
that fix should have generalized to both sentinels. Low contribution; parked
pending a `reproduce.py` that constructs a cyclic deck and asserts the rendered
WHY string contains no phantom `cycle` hop.

## Falsification recipe

Build a two-card cycle (`A advances B`, `B advances A`), run `compute_values`,
feed a resulting `cycle`-terminated path to `_format_why`, and assert the
output trims/labels the sentinel rather than rendering `→ cycle (?)`. If the
trailing-`self` trim added in cc2d4ce already covers `cycle` (re-check the
current `_format_why` body), this is DISPROVED — verify before promoting.

"""Reproduce: the two advance-cycle walkers read opposite edge fields.

`detect_advance_cycles` is the gate `goc validate` runs; it walked
`advanced_by`. `_would_create_advance_cycle` is the guard `goc advance`,
`goc new --advanced-by` and `goc repair-edges` consult before writing an
edge; it walks `advances`. The two fields mirror each other only on a deck
with no half-edges, so where one half of an edge is missing the walkers can
reach opposite verdicts about the same cycle.

Each fixture is a three-card deck whose logical edges are a→b, b→c and,
for the cyclic ones, c→a. The fixtures differ in which field records them:

  advances-only     the card's recipe — every edge only in `advances`
  advanced_by-only  the mirror — every edge only in `advanced_by`
  both fields       control: a cycle as a half-edge-free deck carries it
  acyclic chain     control: a→b→c in both fields, no closing edge

The validator's verdict is whether `detect_advance_cycles` reports anything.
The guard's verdict is whether it refuses any of the deck's own edges,
i.e. whether adding u→v would close a cycle because v already reaches u —
the question the guard answers on every edge it is asked to write.

The controls keep a fix honest: the cycle in both fields must be seen by
both walkers and the acyclic chain by neither, so a change that silenced
one walker or both cannot pass as agreement.

Exit codes follow the deck's reproducer contract:
  0 — the defect no longer fires (the walkers agree on every fixture)
  1 — the defect fires (the walkers disagree on some fixture)
  2 — the harness or a control is broken (a control is misjudged)
"""

from __future__ import annotations

import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc import engine  # noqa: E402

CYCLE = [("a", "b"), ("b", "c"), ("c", "a")]
CHAIN = [("a", "b"), ("b", "c")]


def _deck(edges: list[tuple[str, str]], *, advances: bool, advanced_by: bool) -> list[engine.Card]:
    fm = {t: {"title": t, "status": "open", "advances": [], "advanced_by": []} for t in "abc"}
    for parent, child in edges:
        if advances:
            fm[parent]["advances"].append(child)
        if advanced_by:
            fm[child]["advanced_by"].append(parent)
    return [
        engine.Card(title=t, path=None, frontmatter=fm[t], body="", dod_open=0, dod_done=0)
        for t in "abc"
    ]


def _verdicts(edges: list[tuple[str, str]], **fields: bool) -> tuple[bool, bool, list[str], int, int]:
    cards = _deck(edges, **fields)
    errors = engine.detect_advance_cycles(cards)
    guard = any(engine._would_create_advance_cycle(cards, child, parent) for parent, child in edges)
    # Informational: how `goc repair-edges` would classify the deck's
    # half-edges. Classification simulates repairs in memory, so it gets a
    # fresh deck of its own.
    repair_cards = _deck(edges, **fields)
    fixable, structural = engine._classify_half_edges(engine.find_half_edges(repair_cards), repair_cards)
    return bool(errors), guard, errors, len(fixable), len(structural)


def main() -> int:
    fixtures = [
        ("advances-only", CYCLE, {"advances": True, "advanced_by": False}, None),
        ("advanced_by-only", CYCLE, {"advances": False, "advanced_by": True}, None),
        ("both fields", CYCLE, {"advances": True, "advanced_by": True}, True),
        ("acyclic chain", CHAIN, {"advances": True, "advanced_by": True}, False),
    ]
    disagreements: list[str] = []
    broken_controls: list[str] = []
    for name, edges, fields, expected in fixtures:
        validator, guard, errors, fixable, structural = _verdicts(edges, **fields)
        agree = "agree" if validator == guard else "DISAGREE"
        print(f"{name:17} validator sees cycle: {validator!s:5}  guard sees cycle: {guard!s:5}  -> {agree}")
        for e in errors:
            print(f"{'':17}   validator: {e}")
        if fixable or structural:
            print(f"{'':17}   repair-edges: {fixable} fixable, {structural} structural")
        if expected is not None and (validator, guard) != (expected, expected):
            broken_controls.append(name)
        elif validator != guard:
            disagreements.append(name)
    print()
    if broken_controls:
        print(f"HARNESS: control fixture(s) misjudged: {', '.join(broken_controls)}")
        return 2
    if disagreements:
        print(f"DEFECT: the cycle walkers disagree on: {', '.join(disagreements)}")
        return 1
    print("OK: both cycle walkers reach the same verdict on every fixture")
    return 0


if __name__ == "__main__":
    sys.exit(main())

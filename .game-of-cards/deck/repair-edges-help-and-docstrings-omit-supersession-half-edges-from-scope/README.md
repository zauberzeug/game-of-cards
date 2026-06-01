---
title: repair-edges-help-and-docstrings-omit-supersession-half-edges-from-scope
summary: `goc repair-edges --help` and the verb's docstrings claim the verb only handles `advances/advanced_by` half-edges, but the implementation walks every entry in `INVERSE_REL` (advances/advanced_by AND supersedes/superseded_by) and repairs supersession asymmetries just fine. A user reading `goc validate`'s "Run 'goc repair-edges --apply' to fix" against a supersession half-edge then `goc repair-edges --help` would assume the verb cannot help and try to repair by hand.
status: done
stage: null
contribution: low
created: "2026-06-01T05:00:02Z"
closed_at: "2026-06-01T05:04:01Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation, api-contract]
definition_of_done: |
  - [x] TDD: regression test asserts `_build_parser`'s `repair-edges` help string names both relation classes (the two `advances/advanced_by` strings stop being authoritative).
  - [x] MECHANICAL: subcommand `help=` at `goc/engine.py:2885` mentions supersession scope.
  - [x] MECHANICAL: `_cmd_repair_edges` docstring at `goc/engine.py:4541` mentions supersession scope.
  - [x] MECHANICAL: `find_half_edges` docstring at `goc/engine.py:1447` mentions supersession scope (currently `"Return structured advances↔advanced_by asymmetries."`).
  - [x] PROCESS: log.md closure entry recorded.
worker: {who: "claude[bot]", where: main}
---

# repair-edges-help-and-docstrings-omit-supersession-half-edges-from-scope

## Location

- `goc/engine.py:2885` — subparser `help=` string.
- `goc/engine.py:4541` — `_cmd_repair_edges` docstring.
- `goc/engine.py:1447` — `find_half_edges` docstring.

## What's broken

Three documentation surfaces describe `repair-edges` (and its core
helper `find_half_edges`) as scoped to `advances`/`advanced_by`, but
the implementation iterates **all four** relation fields via
`INVERSE_REL`.

Subparser help (`goc/engine.py:2885`):

```python
p_repair_edges = subparsers.add_parser(
    "repair-edges",
    help="Preview or repair asymmetric advances/advanced_by edges.",
)
```

Verb docstring (`goc/engine.py:4541`):

```python
def _cmd_repair_edges(args):
    """Preview or repair asymmetric advances/advanced_by half-edges."""
```

Helper docstring (`goc/engine.py:1447`):

```python
def find_half_edges(cards: list[Card]) -> list[HalfEdge]:
    """Return structured advances↔advanced_by asymmetries."""
```

But `INVERSE_REL` (`goc/engine.py:824`) declares four entries:

```python
INVERSE_REL = {
    "advances": "advanced_by",
    "advanced_by": "advances",
    "supersedes": "superseded_by",
    "superseded_by": "supersedes",
}
```

…and `find_half_edges` walks every key (`goc/engine.py:1451`):

```python
for field, inverse in INVERSE_REL.items():
```

Empirical confirmation — build a deck with a single supersession
half-edge (`card-a.superseded_by = [card-b]`, `card-b.supersedes =
[]`), run `goc repair-edges` against it: the verb detects the
half-edge and previews a diff that adds `card-a` to
`card-b.supersedes`. So the implementation handles the case; only the
documentation does not.

## Why it matters

Reachability is concrete: `goc validate` calls `find_half_edges`
across all four `INVERSE_REL` fields and, on a supersession half-edge,
prints `"Run 'goc repair-edges --apply' to fix."` (`engine.py` 
validate path). A user who then runs `goc repair-edges --help` reads
that the verb only handles `advances/advanced_by` and may reasonably
conclude the validator's suggestion does not apply to their case —
so they edit the card files by hand, with no diff preview safety net
and a real risk of producing further half-edges.

The same drift appears on `find_half_edges`'s own docstring, which
future contributors read as the contract of the helper. The next
person who adds a relation class to `INVERSE_REL` would not learn
from this docstring that the helper already generalizes.

## Fix

Change the three strings to name both relation classes (or use a
generic "bidirectional edges" phrasing). One concrete option:

- `goc/engine.py:2885` →
  `help="Preview or repair asymmetric advances/advanced_by and supersedes/superseded_by edges."`
- `goc/engine.py:4541` →
  `"""Preview or repair asymmetric bidirectional half-edges (advances/advanced_by, supersedes/superseded_by)."""`
- `goc/engine.py:1447` →
  `"""Return structured bidirectional-edge asymmetries (advances/advanced_by, supersedes/superseded_by)."""`

Add a regression test that builds the argparse parser and asserts the
`repair-edges` help string mentions `supersedes` (or `bidirectional`),
so the next drift gets caught at CI.

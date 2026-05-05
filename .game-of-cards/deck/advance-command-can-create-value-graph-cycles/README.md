---
title: advance-command-can-create-value-graph-cycles
summary: "`goc advance` can add an edge that creates an `advances`/`advanced_by` cycle. The command exits zero and can auto-commit the mutation, but `goc validate` immediately rejects the resulting deck."
status: done
stage: null
contribution: high
created: 2026-05-04
closed_at: 2026-05-05
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] `uv run python deck/advance-command-can-create-value-graph-cycles/reproduce.py` exits zero
  - [x] `goc advance` rejects edge additions that would introduce a cycle
  - [x] Failed cycle attempts leave both cards' relation lists unchanged
  - [x] Regression coverage proves a two-card cycle and a longer transitive cycle are rejected before write/commit
---

# advance-command-can-create-value-graph-cycles

## Location

- `goc/engine.py:441`
- `goc/engine.py:1716`
- `goc/engine.py:1721`
- `goc/engine.py:1725`

## What's broken

`goc validate` rejects cycles in the value-flow graph:

```python
if b == start.title and cur != start.title:
    errors.append(f"{start.title}: advanced_by: cycle detected through {cur} → {b}")
```

But `goc advance` mutates both cards and, depending on auto-commit
policy, can commit the new edge without checking whether the edge makes
the deck invalid:

```python
_mutate_pair(title, advancer, "advanced_by", "advances", add=True)
...
_git_auto_commit([DECK_DIR / title, DECK_DIR / advancer], ...)
```

## Empirical evidence

Current output from `uv run python deck/advance-command-can-create-value-graph-cycles/reproduce.py`:

```text
first_advance_exit=0
first_advance_stdout=advance: card-a.advanced_by += card-b; card-b.advances += card-a
second_advance_exit=0
second_advance_stdout=advance: card-b.advanced_by += card-a; card-a.advances += card-b
validate_exit=1
validate_stderr=ERROR: card-a: advanced_by: cycle detected through card-b → card-a
ERROR: card-b: advanced_by: cycle detected through card-a → card-b
defect present: advance created a relation cycle that validate rejects
```

## Why it matters

The relation commands should preserve deck invariants. A command that can
leave `goc validate` failing makes pre-commit/CI catch a problem only
after the deck has already been mutated, and auto-commit can make the bad
state visible to other agents.

## Fix

Before writing an added edge, compute whether `advancer -> title` would
create a cycle in the `advances` graph. If so, print a Click error and
exit non-zero without changing either README. Keep `unadvance` as the
repair path for existing cycles.

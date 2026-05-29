---
title: compute-values-iterates-non-list-advances-character-by-character
summary: "`compute_values` iterates `frontmatter['advances']` without an `isinstance(..., list)` guard, so a hand-edited bare-string `advances: bcard` is walked character-by-character on the always-run render path: each char becomes a phantom edge target. Result is spurious per-char dangling-edge warnings on every `goc` / `goc --board` call plus a silently inflated priority value, and `goc validate` does not gate the render path."
status: done
stage: null
contribution: medium
created: "2026-05-27T14:01:31Z"
closed_at: "2026-05-29T04:24:07Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — a card with a bare-string `advances` value gets its own rank (1.0 for `low`), not the cycle-inflated 1.7, and emits no phantom per-character dangling-edge warnings.
  - [x] TDD: a regression test in tests/ asserts `compute_values` treats a non-list `advances` (and `advanced_by`, exercised by the cycle walkers) as an empty edge set, matching `find_half_edges` and `validate_card`.
  - [x] MECHANICAL: the `for dest in ... or []` loop at goc/engine.py:1836 (and the parallel walkers in `value_for` / the cycle detectors that read the same field) guards the value with `isinstance(..., list)` before iterating, mirroring the guard already present at engine.py:1297.
  - [x] PROCESS: full regression suite green (`uv run python -m unittest discover -s tests`); plugin mirrors synced if engine.py changed (pre-commit `sync-plugin-assets`).
worker: {who: "claude[bot]", where: main}
---

# `compute_values` iterates a non-list `advances` field character-by-character

## Location

`goc/engine.py:1836` — inside `compute_values`'s `value_for` recursion:

```python
for dest in t.frontmatter.get("advances") or []:
    if dest not in by_title:
        ...  # emit "dangling advances edge" warning, continue
```

## What's broken

`advances` is contractually a **list** of card titles. The validator
knows this — `validate_card` flags a non-list value (engine.py:1235):

```python
if v and not isinstance(v, list):
    errors.append(f"{t.title}: {field}: must be a list")
```

and `find_half_edges` guards against it (engine.py:1297):

```python
if not isinstance(v, list):
    continue
```

But `compute_values` — which runs on **every** `goc` and `goc --board`
invocation, a path that is *not* gated by `goc validate` — has no such
guard. When a card's frontmatter is hand-edited to the YAML scalar form
`advances: bcard` (a bare string instead of a list), Python iterates the
string **character by character**. Each character is treated as a target
card title:

- chars with no matching card (`b`, `c`, `r`, `d`) each fire a phantom
  `WARN dangling advances edge: a → 'b' ...` on stderr;
- a char that happens to equal the card's own title (`a`) re-enters
  `value_for`, hits the `if title in in_progress` cycle branch, and
  returns `own`, which then amplifies the parent: `best = own`, final
  value `own + γ·own`.

The defensive cycle branch's own docstring (engine.py:1808-1820) promises
it is "unreachable defensive code on any valid deck" — but a bare-string
`advances` reaches it without any real cycle, and the docstring's claim
that unknown targets "are skipped for the priority math AND surfaced once
per (card, target) pair" describes real edges, not per-character phantoms.

## Empirical evidence

`uv run python .game-of-cards/deck/compute-values-iterates-non-list-advances-character-by-character/reproduce.py`:

```
WARN dangling advances edge: a → 'b' (target card not found; priority math drops the edge). Run 'goc validate' for the authoritative report.
WARN dangling advances edge: a → 'c' (target card not found; priority math drops the edge). Run 'goc validate' for the authoritative report.
WARN dangling advances edge: a → 'r' (target card not found; priority math drops the edge). Run 'goc validate' for the authoritative report.
WARN dangling advances edge: a → 'd' (target card not found; priority math drops the edge). Run 'goc validate' for the authoritative report.
contribution 'low' bare rank          : 1.0
compute_values value for card 'a'      : 1.7
value path                             : ['a', 'cycle']
DEFECT CONFIRMED: value is 1.7, expected 1.0 ...
```

A leaf card with no real descendants should value at its own rank (1.0);
instead it reports **1.7** (1.0 + 0.7·1.0), a 70% inflation, with a
nonsense `['a', 'cycle']` value path.

## Why it matters

The render path is the one place a malformed-but-unvalidated deck is
read silently. A consuming repo that hand-edits frontmatter and hasn't
run `goc validate` gets (a) stderr noise on every queue listing, and (b)
priority values that are wrong in a direction the sort then acts on —
the card jumps the queue. The asymmetry is the real defect: two of the
three sites that read this field already guard it; the value walk, the
highest-leverage consumer, does not.

## Fix (applied)

`isinstance(..., list)` guards added to the three walker sites named in
the DoD, mirroring the existing pattern at engine.py:1297:

- `compute_values.value_for` (engine.py:1836) — non-list `advances`
  is treated as an empty edge set, so no character-by-character
  iteration, no phantom dangling-edge warnings, no chance self-match
  on the in-progress cycle branch. Reproduce.py now reports the leaf's
  own rank (1.0) with `path == ["self"]`.
- `detect_advance_cycles` (engine.py:1323) — non-list `advanced_by`
  skipped at the walker step.
- `_would_create_advance_cycle` (engine.py:1349) — non-list `advances`
  skipped at the walker step.

The `compute_values` docstring was updated to record the new defensive
guard alongside the existing in-progress / dangling-edge notes.

`goc validate` remains the authoritative reporter; this change only
stops the render path from manufacturing phantom edges and bogus
values from a non-list.

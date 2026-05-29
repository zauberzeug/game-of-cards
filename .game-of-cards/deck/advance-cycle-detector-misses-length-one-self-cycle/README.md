---
title: advance-cycle-detector-misses-length-one-self-cycle
summary: "`detect_advance_cycles` (and its mirror `detect_supersedes_cycles`) excludes the start node from the cycle check (`cur != start.title`), so a length-1 self-edge (`advanced_by: [self]` / `superseded_by: [self]`) produces no cycle error from these detectors. Currently MASKED: full `goc validate` rejects any self-reference earlier via the per-field check at engine.py:1163, so this is latent defense-in-depth rot, not a user-observable escape. Unverified — no reproduce.py proving a user-facing failure."
status: disproved
stage: null
contribution: low
created: "2026-05-27T01:54:46Z"
closed_at: "2026-05-27T02:03:37Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, unverified, api-contract]
definition_of_done: |
  - [ ] PROCESS: decide whether this latent gap is worth fixing given the per-field self-reference check (engine.py:1163) already rejects self-edges in full validate. If yes, proceed; if no, disprove with that rationale recorded in log.md.
  - [ ] TDD: if fixed, a card with `advanced_by: [<its-own-title>]` produces a cycle error from `detect_advance_cycles` directly (not only from the per-field check); same for `detect_supersedes_cycles` with a `superseded_by` self-edge.
  - [ ] MECHANICAL: if fixed, promotion — drop the `unverified` tag once a reproduce.py demonstrates a path where the per-field check does NOT run but the cycle detector does (e.g. a programmatic caller of `detect_advance_cycles` outside `validate`).
---

# `detect_advance_cycles` cannot flag a length-1 (self) cycle

## Verdict (disproved 2026-05-27)

**Disproved as a reachable defect.** The blind spot in the code is real
(the `cur != start.title` guard does suppress the length-1 self-cycle
case), but it is not a user-observable bug and the card's own promotion
conditions do not hold:

- The only callers of `detect_advance_cycles` / `detect_supersedes_cycles`
  are inside `goc validate` (`engine.py:2558` and `engine.py:2561`).
- `validate` runs `validate_card` on every card *first* (`engine.py:2541`),
  which includes the per-field self-reference check at `engine.py:1163`
  that rejects any `advances` / `advanced_by` / `superseded_by` entry equal
  to the card's own title. A self-edge therefore fails validation before
  the cycle detectors ever run.
- There is **no caller of the cycle detectors that bypasses the per-field
  check** (grepped 2026-05-27 — `engine.py:2558`/`2561` are the only two,
  both downstream of `validate_card`). So the recipe's promotion condition
  #1 (an unmasked direct caller) is false, and condition #2 (the per-field
  check refactored away) has not happened.

The MECHANICAL DoD item — drop `unverified` once a reproduce.py exercises a
path where the per-field check does not run but the detector does — is
therefore unsatisfiable: no such path exists. "Fixing" the guard would only
add a redundant second error message for self-edges that `validate` already
rejects. Closing as disproved per the card's stated falsification recipe.

If condition #2 ever changes (the per-field self-reference check is removed
or narrowed), re-file: at that point the guard becomes a live escape and
the one-line fix (drop `cur != start.title` in both detectors) is warranted.

## Hypothesis (file:line)

`goc/engine.py:1249`:

```python
for b in advanced_by:
    if b == start.title and cur != start.title:
        errors.append(f"{start.title}: advanced_by: cycle detected through {cur} → {b}")
    stack.append(b)
```

The guard `cur != start.title` deliberately excludes the start node from
the back-edge test. For a self-edge — a card whose `advanced_by` lists
its own title — the only iteration where `b == start.title` is the one
where `cur == start.title`, which the guard suppresses. So the detector
never reports a length-1 cycle. The supersession mirror has the identical
shape at `goc/engine.py:1303`.

## Why this is currently masked (and why it's `unverified`)

End-to-end `goc validate` rejects any relationship field that references
its own title via the per-field self-reference check at
`goc/engine.py:1163`:

```python
for ref in v:
    if ref == t.title:
        errors.append(f"{t.title}: {field}: self-reference '{ref}'")
```

That check runs for `advances`, `advanced_by`, and `superseded_by`
before a user could observe the cycle detector's blind spot. So today
there is **no user-observable escape** — the defect is dead
defense-in-depth, not a live bug. That is exactly why it is filed
`unverified`: there is no reproduce.py that prints a wrong result
through the public `goc validate` surface.

## Falsification / promotion recipe

Promote (drop `unverified`, file a real fix) only if one of these holds:

1. A code path calls `detect_advance_cycles` / `detect_supersedes_cycles`
   *without* first running the per-field self-reference check
   (engine.py:1163) — at which point a self-edge would slip through. Grep
   for direct callers; if found, write a reproduce.py exercising that
   path.
2. The per-field check is ever refactored away or narrowed, removing the
   masking layer.

Otherwise this is a candidate to **disprove** with the rationale "the
length-1 case is unreachable because the per-field check rejects all
self-references first" recorded in log.md.

Surfaced by: audit-deck general-purpose hunter, 2026-05-27 (candidate #2 of 3).

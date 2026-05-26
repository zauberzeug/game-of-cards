---
title: mutual-supersession-passes-validation-and-creates-forward-pointer-cycle
summary: "`goc status A superseded --by B` then `goc status B superseded --by A` is fully permitted: at the second call B's status is still `open` (only `B.supersedes` was touched), so the terminal-status guard never fires and there is no check that the successor already supersedes the holder. The result is A.superseded_by=[B], B.superseded_by=[A] — a mutual supersession cycle that passes every validator (`detect_advance_cycles` is advances-only; no `detect_supersedes_cycles` exists). A reader routed forward through `superseded_by` loops forever."
status: open
stage: null
contribution: high
created: "2026-05-26T20:54:24Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — a mutual supersession pair is either rejected at construction time or flagged by `goc validate` (the forward-pointer walk no longer cycles).
  - [ ] TDD: `goc status B superseded --by A` is rejected when A is already `superseded_by B` (or A already `supersedes` B), with a message naming the cycle — mirroring the advances-cycle guard.
  - [ ] TDD: `goc validate` flags any pre-existing mutual/longer supersession cycle (a `detect_supersedes_cycles` analogous to `detect_advance_cycles`, OR an extension that covers the supersession edge set).
  - [ ] MECHANICAL: the false-premise comment at `goc/engine.py:3586-3588` ("Supersession edges can't form a cycle ...") is corrected or removed.
  - [ ] TDD: `uv run goc validate` passes on this repo's deck (no false positives on the legitimate single-direction supersession links already present).
---

# Mutual supersession passes validation and creates a forward-pointer cycle

## Location

- `goc/engine.py:3356` — the `goc status` terminal-status guard, which
  checks only the *holder's* status, not the successor's.
- `goc/engine.py:3329-3375` — `_cmd_status` with `--by`: no check that
  the successor already supersedes the holder.
- `goc/engine.py:3585-3588` — the false-premise comment asserting
  supersession edges can't cycle.
- `goc/engine.py:1172` (`detect_advance_cycles`) — advances-only; there
  is no `detect_supersedes_cycles` counterpart.

## What's broken

`goc status <title> superseded --by <successor>` (`_cmd_status`,
`goc/engine.py:3329-3375`) does three things: loads the successor to
confirm it exists, flips the holder's status to `superseded`, and calls
`_mutate_pair(title, successor, "superseded_by", "supersedes", add=True)`.
The only cycle-relevant guard is the terminal-status check, which
inspects the **holder**, not the successor:

```python
if prior in TERMINAL_STATUSES:
    print(f"ERROR: {title}: status is {prior!r} (terminal); ...")
    sys.exit(2)
```

So the sequence:

1. `goc status A superseded --by B` → `A.status=superseded`,
   `A.superseded_by=[B]`, `B.supersedes=[A]`. **`B.status` stays `open`.**
2. `goc status B superseded --by A` → `prior = B.status = open` (NOT
   terminal — only `B.supersedes` was touched in step 1), so the guard
   passes. Sets `B.status=superseded`, `B.superseded_by=[A]`,
   `A.supersedes=[B]`.

Nothing rejects step 2 even though A already lists B in `superseded_by`.
The end state is a mutual cycle: `A.superseded_by=[B]`,
`B.superseded_by=[A]`, both `superseded`.

A comment at `goc/engine.py:3586` asserts this is impossible:

```python
# Supersession edges can't form a cycle (a superseded card is terminal
# and won't re-enter the relationship graph), so the check only applies
# to the advances pair.
```

This is false. "Terminal" is a per-card status, not a graph-reachability
property; `_cmd_status` makes the holder terminal but never the
successor, so the successor is free to be superseded back. And no
validator catches the resulting cycle: `detect_advance_cycles`
(`goc/engine.py:1172`) walks the **advances** graph only,
`validate_bidirectional_edges` only checks edge symmetry (which a mutual
cycle satisfies), and `validate_supersedes_targets` only checks that each
target is `status: superseded` (which both are). There is no
`detect_supersedes_cycles`.

The deck doc (`AGENTS.md`) promises: "a reader landing on a `superseded`
card can be routed forward without parsing prose." A forward walk through
`superseded_by` on a cycle never terminates.

## Empirical evidence

`reproduce.py` builds the mutual end-state in a temp deck, runs every
supersession-relevant validator, and walks the forward pointer. See the
script output (exit 1 = defect fires): all validators return no errors
*and* the `superseded_by` walk detects a cycle.

## Why it matters

Supersession is the deck's "record axis" routing primitive — `goc validate`
is meant to enforce referential integrity for it the same way it does for
advances. A mutual (or longer) supersession cycle is accepted silently,
and any consumer that follows `superseded_by` to find the live successor
(a "this card was replaced by …" walk) hangs. The advances graph already
has `detect_advance_cycles` precedent
([advance-command-can-create-value-graph-cycles](../advance-command-can-create-value-graph-cycles/),
done); the supersession edge set has no equivalent.

## Fix

Two complementary changes (both, ideally):

1. **Reject at construction.** In `_cmd_status` (`goc/engine.py`), before
   committing a `--by` supersession, refuse when the successor already
   reaches the holder through `superseded_by` (the analog of
   `_would_create_advance_cycle`). Exit non-zero with a message naming
   the cycle.
2. **Catch at validate.** Add a `detect_supersedes_cycles` mirroring
   `detect_advance_cycles` (walk `superseded_by` / `supersedes`), wired
   into `_cmd_validate` alongside the advances-cycle check. Correct or
   delete the false-premise comment at `goc/engine.py:3586`.

Do NOT apply the fix as part of filing this card.

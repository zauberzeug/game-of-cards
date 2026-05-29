---
title: goc-unadvance-with-self-target-leaves-card-in-half-edge-state
summary: "`goc unadvance <title> --by <title>` accepts a self-target call where `goc advance <title> --by <title>` rejects it (`ERROR: cannot advance a card with itself`). The asymmetry is a missing guard in `_cmd_unadvance`. When a card already carries self-edges on disk (manual edit, third-party import, or future caller that bypasses `_cmd_advance`'s guard), `_mutate_pair` captures `parent_text` before the first write — so the second write reverts one side and leaves a half-edge that `goc validate` rejects."
status: open
stage: null
contribution: medium
created: "2026-05-29T20:55:49Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — `goc unadvance foo --by foo` on a card with self-edges (`advances: [foo]`, `advanced_by: [foo]`) either errors out at exit 2 (chosen path A) OR cleanly clears BOTH lists (chosen path B), but no longer leaves the card in a half-edge state.
  - [ ] PROCESS: decision recorded on whether `_cmd_unadvance` rejects self-target like `_cmd_advance` (caller-level guard, mirrors engine.py:4388-4390) OR `_mutate_pair` learns to handle child==parent correctly (helper-level guard, also covers any future `_cmd_repair_edges` self-edge repair). The chosen path is reflected in the body's "Fix" section before implementation.
  - [ ] MECHANICAL: `_cmd_unadvance` (engine.py:4403) and/or `_mutate_pair` (engine.py:4180) carries the guard described in the decision. The output of `goc unadvance foo --by foo` matches the chosen failure mode (ERROR + exit 2, OR clean removal of both halves).
  - [ ] TDD: a regression test in `tests/` asserts the chosen behavior for the self-target case (both the no-edge variant and the on-disk self-edge variant).
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` stay green.
---

# `goc unadvance` with self-target leaves card in half-edge state

## Location

- `goc/engine.py:4403-4414` — `_cmd_unadvance` (no self-target guard).
- `goc/engine.py:4382-4400` — `_cmd_advance` (has the guard at lines 4388-4390).
- `goc/engine.py:4180-4193` — `_mutate_pair` (reads `parent_text` before the first write, so child==parent makes the second write revert the first).

## What's broken

`_cmd_advance` explicitly rejects self-target:

```python
# goc/engine.py:4388
if title == advancer:
    print("ERROR: cannot advance a card with itself", file=sys.stderr)
    sys.exit(2)
```

`_cmd_unadvance` has no equivalent guard:

```python
# goc/engine.py:4403
def _cmd_unadvance(args):
    """Remove bidirectional value-flow edge."""
    title = args.title
    advancer = args.advancer
    commit = args.commit
    no_commit = args.no_commit
    _mutate_pair(title, advancer, "advanced_by", "advances", add=False)
    print(f"unadvance: {title}.advanced_by -= {advancer}; {advancer}.advances -= {title}")
    ...
```

The mirrored helper `_mutate_pair` reads both copies of the README before
either write, which is incorrect when `child_title == parent_title`:

```python
# goc/engine.py:4180
def _mutate_pair(child_title, parent_title, field_on_child, field_on_parent, *, add):
    child_dir = DECK_DIR / child_title
    parent_dir = DECK_DIR / parent_title
    load_card_or_exit(child_dir, child_title)
    load_card_or_exit(parent_dir, parent_title)
    op = _add_to_list_field if add else _remove_from_list_field
    child_text = (child_dir / "README.md").read_text()
    parent_text = (parent_dir / "README.md").read_text()
    (child_dir / "README.md").write_text(op(child_text, field_on_child, parent_title))
    (parent_dir / "README.md").write_text(op(parent_text, field_on_parent, child_title))
```

When `child_dir == parent_dir`, the second `.write_text` writes the result of
operating on `parent_text` — the file content as it was *before* the first
write — so the first write's effect on the unrelated field is silently
reverted.

## Empirical evidence

Reproducer (see `reproduce.py`):

```
--- BEFORE: foo card frontmatter ---
advances:
  - foo
advanced_by:
  - foo
--- run: goc unadvance foo --by foo ---
unadvance: foo.advanced_by -= foo; foo.advances -= foo
exit=0
--- AFTER ---
advances: []
advanced_by:
  - foo
```

Two distinct symptoms:

1. The verb prints a confident "removed both halves" message and exits 0
   even though `goc advance foo --by foo` (its mirror) refuses the same
   shape with `ERROR: cannot advance a card with itself`.
2. The on-disk state is now `advances: []`, `advanced_by: [foo]` — a
   half-edge. `goc validate` would flag this as an
   `advanced_by_missing_advances` half-edge needing repair.

## Why it matters

`_cmd_advance` blocks `title == advancer` at filing time, so a card cannot
*acquire* a self-edge through the normal CLI. But self-edges can land on
disk via:

- manual file editing during a triage / refactor / migration session
- a third-party import script or `goc migrate-list-style`-style bulk
  rewrite that mishandles the frontmatter
- any future engine caller that invokes `_mutate_pair` directly with
  `child==parent` (e.g. a `_cmd_repair_edges` repair where `edge.ref ==
  edge.src` for a self half-edge)

In all three reachability paths, the user's recovery move is `goc unadvance
<title> --by <title>` — the verb whose name and `--help` text both promise
to remove a self-targeted edge. Today that move corrupts the card further
instead of clearing it. The success message conceals the corruption from
the user, who only notices when the next `goc validate` flags a half-edge
on a card they thought they'd just cleaned up.

## Decision required

Two credible fix shapes; the maintainer should pick one before
implementation.

### Option A — caller-level guard (mirrors `_cmd_advance`)

Add the same five-line guard to `_cmd_unadvance` that `_cmd_advance` has.
Simplest and most local; symmetric with the existing pattern.

```python
def _cmd_unadvance(args):
    """Remove bidirectional value-flow edge."""
    title = args.title
    advancer = args.advancer
    if title == advancer:
        print("ERROR: cannot unadvance a card with itself", file=sys.stderr)
        sys.exit(2)
    ...
```

- **Pro:** symmetric with `_cmd_advance`; trivial diff; one-line behavior
  contract.
- **Pro:** rejects the corruption path before it can fire.
- **Con:** leaves any direct `_mutate_pair(self, self, ...)` caller
  (current or future — `_cmd_repair_edges` is the candidate) susceptible
  to the same half-edge bug if a self half-edge ever lands on disk.

### Option B — helper-level guard in `_mutate_pair`

Push the guard down into `_mutate_pair` so the centralized helper handles
child==parent correctly (either by rejecting, or by reading the file once
and applying both field updates to a single in-memory copy before writing).

```python
def _mutate_pair(child_title, parent_title, field_on_child, field_on_parent, *, add):
    if child_title == parent_title:
        # Single-file update — read once, apply both field ops, write once.
        ...
```

- **Pro:** also fixes any `_cmd_repair_edges` repair of a self half-edge,
  not just the user-driven `unadvance` path.
- **Pro:** lets `_cmd_advance`'s existing caller-level guard be retired
  (or kept as a fast-fail with a clearer message).
- **Con:** larger change; needs a clear chosen behavior (reject vs. handle
  cleanly) and a regression test covering both forms.
- **Con:** the existing self-target guard in `_cmd_advance` becomes a
  redundant second error path unless removed.

The asymmetric API contract (Option A's framing) and the centralized helper
correctness (Option B's framing) are both real concerns. Pick one shape
before writing the test.

## Fix

To be written after the decision is recorded — see "Decision required".
Whichever path is chosen, the regression test in `tests/` must cover:

1. The no-self-edge case: `unadvance foo --by foo` on a card with empty
   `advances` / `advanced_by` lists.
2. The on-disk self-edge case: `unadvance foo --by foo` on a card with
   self-edges present in both lists (the reproducer's setup).

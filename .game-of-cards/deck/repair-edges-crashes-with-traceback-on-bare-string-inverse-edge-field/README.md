---
title: repair-edges-crashes-with-traceback-on-bare-string-inverse-edge-field
summary: "`goc repair-edges` and `goc advance` die with an uncaught `ValueError` traceback when an inverse edge field is a bare-string scalar — the exact corruption `goc validate` flags and tells the user to run `goc repair-edges --apply` to fix. The half-edge DETECTOR (`find_half_edges`) tolerantly coerces a bare-string inverse field to `[]` and emits a half-edge, but the REPAIRER (`_add_to_list_field`) rejects that same shape with `raise ValueError`, which is uncaught up through `_repair_edge_diff` / `_cmd_repair_edges` / `_mutate_pair`. The repair tool crashes on the corruption it is pointed at."
status: open
stage: null
contribution: medium
created: "2026-06-23T19:06:52Z"
closed_at: null
human_gate: decision
advances:
  - bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] PROCESS: confirm the fix direction with the umbrella card's chosen approach (A loader-time rejection/coercion, B centralized `_field_as_list` helper, C per-consumer guard) — record the resolution in log.md. See `## Decision required`.
  - [ ] TDD: reproduce.py exits zero today (defect fires); after the fix it exits non-zero (`_repair_edge_diff` no longer raises, or the load fails cleanly before repair is attempted).
  - [ ] TDD: a regression test asserts `goc repair-edges` (dry run) and `goc repair-edges --apply` on a deck with a bare-string inverse edge field produce a clean outcome (either a repaired list or a non-traceback error with a clear message), never an uncaught `ValueError`.
  - [ ] TDD: the same regression covers `goc advance <child> --by <parent>` (the `_mutate_pair` add path) on a bare-string endpoint field — same clean-outcome assertion.
  - [ ] MECHANICAL: `goc validate`'s "Run 'goc repair-edges --apply' to fix." guidance and the repair path agree — the recommended command no longer crashes on the input validate flags.
---

# repair-edges-crashes-with-traceback-on-bare-string-inverse-edge-field

`goc repair-edges` — the tool `goc validate` explicitly recommends to repair
half-edges — crashes with an uncaught `ValueError` traceback when the inverse
edge field on the endpoint card is a bare-string scalar instead of a list. The
same crash hits `goc advance <child> --by <parent>` (and the other
`_mutate_pair` add callers: `goc new --advanced-by`, `goc status … superseded
--by`).

## Location

- `goc/engine.py:4906-4916` — `_add_to_list_field` (the repairer; raises).
- `goc/engine.py:4951-4966` — `_repair_edge_diff` (calls it in the dry-run preview).
- `goc/engine.py:4928-4941` — `_mutate_pair` (calls it via `--apply`, `advance`, `new`, `superseded --by`).
- `goc/engine.py:1678-1696` — `find_half_edges` (the detector; tolerates the bare string).

## What's broken

The detector and the repairer disagree about whether a bare-string inverse
field is acceptable input.

The DETECTOR coerces a non-list inverse field to `[]`, so it *emits* a
half-edge for it (`engine.py:1691-1693`):

```python
inverse_list = other.frontmatter.get(inverse) or []
if not isinstance(inverse_list, list):
    inverse_list = []
if t.title not in inverse_list:
    half_edges.append(HalfEdge(t.title, field, ref, inverse))
```

The REPAIRER refuses the very same shape with an uncaught `raise`
(`engine.py:4906-4911`):

```python
def _add_to_list_field(text: str, field: str, title_to_add: str) -> str:
    """Add title_to_add to a frontmatter list field, idempotent."""
    fm, body = parse_frontmatter(text)
    cur = fm.get(field) or []
    if not isinstance(cur, list):
        raise ValueError(f"{field}: not a list")
```

No caller in the `_repair_edge_diff` → `_cmd_repair_edges` chain, nor in
`_mutate_pair`, wraps this in a `try`/`except`, so it surfaces as a raw Python
traceback and exit 1.

Meanwhile `goc validate` flags the field and points the user straight at the
crashing command:

```
ERROR: card-b: advanced_by: must be a list
ERROR: card-a: advances contains 'card-b' but card-b.advanced_by is missing 'card-a' (half-edge)
Run 'goc repair-edges --apply' to fix.
```

## Empirical evidence

`uv run python .game-of-cards/deck/repair-edges-crashes-with-traceback-on-bare-string-inverse-edge-field/reproduce.py`:

```
DETECTOR: find_half_edges reports 1 half-edge(s)
  repair_title='card-b' repair_field='advanced_by' repair_value='card-a'

REPAIRER: _repair_edge_diff on that same half-edge:
  CRASHED with uncaught ValueError:
Traceback (most recent call last):
  ...
  File ".../goc/engine.py", line 4954, in _repair_edge_diff
    repaired = _add_to_list_field(original, edge.repair_field, edge.repair_value)
  File ".../goc/engine.py", line 4911, in _add_to_list_field
    raise ValueError(f"{field}: not a list")
ValueError: advanced_by: not a list

CONFIRMED: the validator-recommended repair path raises ValueError('advanced_by: not a list') instead of repairing the bare-string field.
```

Live CLI confirmation against a throwaway deck (`card-a.advances: [card-b]`,
`card-b.advanced_by: card-a` as a bare string):

- `goc repair-edges` (dry run) → traceback ending `ValueError: advanced_by: not a list` at `engine.py:4954 → 4911`.
- `goc repair-edges --apply` → same traceback via `_cmd_repair_edges → _mutate_pair → 4911`.
- `goc advance card-b --by card-a` → same `ValueError` traceback.

## Why it matters

The reachability path is the validator itself. A hand-edited card (or a
one-shot-authored card) that writes `advanced_by: card-a` instead of
`advanced_by:\n- card-a` is a real, recoverable deck state — and `goc validate`
already detects it, names it a half-edge, and instructs the user to run
`goc repair-edges --apply`. Following that instruction crashes with a Python
traceback instead of repairing the edge, leaving the user with no in-tool path
out of a state the tool itself told them was fixable. The semantically correct
reference (`card-a`) is sitting right there in the field; only the YAML shape
is wrong.

This is a new instance of the family tracked by
[bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes](../bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes/),
whose DoD currently treats `_add_to_list_field`'s `isinstance(..., list)`
check as the *correct* sibling guard. The novel, load-bearing observation: that
guard's `raise` is uncaught, so it converts a recoverable corruption into an
unhandled crash in the one tool meant to recover it — a detector/repairer
asymmetry, not just another silently-iterating consumer.

## Decision required

The fix direction is governed by the umbrella card's approach choice, but the
local options are:

1. **Coerce-and-repair** — in `_add_to_list_field`, treat a non-list `cur` the
   way `find_half_edges` does: if it is a bare string, normalize to a list
   (either `[]` then append, or `[cur]` then append to preserve the existing
   value) and proceed. This makes `repair-edges` actually repair the
   corruption validate flags. Risk: silently rewriting a field whose bare
   value differs from the edge being added.
2. **Clean diagnostic, non-traceback exit** — catch the `ValueError` in
   `_repair_edge_diff` / `_cmd_repair_edges` / `_mutate_pair` and surface the
   validator's "must be a list" message with a non-zero exit and a per-card
   pointer, so the crash becomes an actionable error.
3. **Route through the umbrella's chosen shared helper** (approach B there): if
   a centralized `_field_as_list` shape-coercer lands, `_add_to_list_field`
   reads through it and the asymmetry disappears at the source.

Recommended: align with whatever the umbrella card decides; if that card is
still open at implementation time, option 1 (coerce-and-repair) most directly
honors validate's own "this is fixable" promise. A human/decision is needed
because option 1 changes write behavior on malformed input (value-preservation
question) and the broader approach is owned by the umbrella card.

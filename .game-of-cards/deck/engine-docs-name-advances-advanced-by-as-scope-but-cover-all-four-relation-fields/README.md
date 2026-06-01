---
title: engine-docs-name-advances-advanced-by-as-scope-but-cover-all-four-relation-fields
summary: Generalization of `repair-edges-help-and-docstrings-omit-supersession-half-edges-from-scope`. Multiple strings in `goc/engine.py` (and AGENTS.md) still say "advances/advanced_by" when describing scope, but the underlying code path now operates on every entry in `_BLOCK_LIST_FIELDS` / `INVERSE_REL` / `LIST_REL_FIELDS` — including `supersedes/superseded_by`. The `repair-edges` sweep fixed three of these; the remaining drift sites span `emit_frontmatter`, the `migrate-list-style` verb, and the AGENTS.md card-authoring rules.
status: active
stage: null
contribution: low
created: "2026-06-01T05:05:32Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation, api-contract, meta-fix]
definition_of_done: |
  - [ ] MECHANICAL: `emit_frontmatter` docstring at `goc/engine.py:305-306` names all four `_BLOCK_LIST_FIELDS` (`advances`, `advanced_by`, `supersedes`, `superseded_by`) rather than just `advances`/`advanced_by`.
  - [ ] MECHANICAL: `migrate-list-style` subparser `help=` at `goc/engine.py:2935` mentions all four relation fields (or the `_BLOCK_LIST_FIELDS` set generically).
  - [ ] MECHANICAL: `_cmd_migrate_list_style` docstring at `goc/engine.py:5099` mentions all four relation fields.
  - [ ] MECHANICAL: "All cards already use block-style" message at `goc/engine.py:5125` is generalized to the relation-edge set.
  - [ ] MECHANICAL: AGENTS.md card-authoring section ("YAML format for list fields") generalizes the rule from `advances`/`advanced_by` to all bidirectional-edge list fields.
  - [ ] TDD: regression test asserts every user-facing scope string for these surfaces mentions `supersedes` (or names `_BLOCK_LIST_FIELDS` generically), so the next time a new relation class is added the drift fails CI.
  - [ ] PROCESS: log.md closure entry recorded.
worker: {who: "claude[bot]", where: main}
---

# engine-docs-name-advances-advanced-by-as-scope-but-cover-all-four-relation-fields

## Pattern

`goc/engine.py` declares four list-relation field tuples / frozensets:

```python
LIST_REL_FIELDS = ("advances", "advanced_by", "supersedes", "superseded_by")  # 821
_BLOCK_LIST_FIELDS = frozenset({"advances", "advanced_by", "supersedes", "superseded_by"})  # 280
INVERSE_REL = {"advances": "advanced_by", ..., "supersedes": "superseded_by", ...}  # 824
```

…but several user-facing strings still describe the scope as
`advances/advanced_by` only. A reader who sees these strings reads the
narrower scope as the truth, and either edits supersession fields by
hand (already filed and closed as
[`repair-edges-help-and-docstrings-omit-supersession-half-edges-from-scope`](../repair-edges-help-and-docstrings-omit-supersession-half-edges-from-scope/))
or assumes a verb cannot help with their supersession-bearing card.

## Drift sites (remaining after the `repair-edges` closure)

1. **`emit_frontmatter` docstring** (`goc/engine.py:305-306`):
   > "`advances` and `advanced_by` use block-style lists (one `- item`
   > per line) when non-empty; empty lists still render as `[]`."

   Behavior covers the full `_BLOCK_LIST_FIELDS` set (`engine.py:316`):
   `if key in _BLOCK_LIST_FIELDS and isinstance(value, list) and value:`.

2. **`migrate-list-style` subparser `help=`** (`goc/engine.py:2935`):
   `help="Re-emit every card to convert advances/advanced_by to block-style lists."`

   Behavior: it re-emits frontmatter through `emit_frontmatter`, which
   block-styles every relation list — not just advances.

3. **`_cmd_migrate_list_style` docstring** (`goc/engine.py:5099`):
   `"""Re-emit every card to convert advances/advanced_by to block-style lists."""`

4. **`migrate-list-style` no-op message** (`goc/engine.py:5125`):
   `print("All cards already use block-style for advances/advanced_by — nothing to do.")`

5. **AGENTS.md card-authoring rules** (`AGENTS.md`, "YAML format for
   list fields" bullet):
   > "**YAML format for list fields:** `advances` and `advanced_by`
   > use block-style (one `- item` per line) when non-empty; empty
   > lists stay as `[]`."

## Why it matters

Reachability: each of these strings is read by a user (CLI `--help`
listing, source-code reader, AGENTS.md card-authoring contributor)
before they reach for the underlying code. A new relation class added
to `INVERSE_REL` (the supersession pair was the first such addition;
future classes are plausible) would silently extend the gap unless the
documentation surfaces are explicitly enumerated against
`_BLOCK_LIST_FIELDS` / the relation-set constants.

The CI regression bar: the closed `repair-edges` card added a test
that introspects the parser action's `help=` and the function
docstrings. Generalizing that test to the migrate-list-style surfaces
keeps the same drift from recurring in adjacent verbs.

## Fix

Rewrite the five drift strings to use either explicit four-field
enumeration or a generic "bidirectional-edge list fields" phrasing,
and extend the regression test (`tests/test_repair_edges.py`
introduced
`test_repair_edges_help_names_both_relation_classes`) so that
`migrate-list-style` help + docstring are checked the same way.

For AGENTS.md: rewrite the bullet to generalize ("All four list
relation fields — `advances`, `advanced_by`, `supersedes`,
`superseded_by` — use block-style …").

No code-path change is needed — the implementation already covers all
four fields uniformly.

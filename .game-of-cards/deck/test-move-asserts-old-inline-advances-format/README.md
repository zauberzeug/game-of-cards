---
title: test-move-asserts-old-inline-advances-format
summary: "tests/test_install.py::test_move_renames_without_redirect_and_rewrites_relations asserts the parent card's frontmatter contains `advances: [renamed-card]` (inline flow style). The emitter was switched to block style by emit-advances-and-advanced-by-as-block-style-yaml-lists, so the actual output is `advances:\\n  - renamed-card`. Test now fails on every push to main."
status: active
stage: null
contribution: medium
created: 2026-05-08
closed_at: null
human_gate: none
advances: []
advanced_by:
  - emit-advances-and-advanced-by-as-block-style-yaml-lists
tags: [bug, api-contract]
definition_of_done: |
  - [ ] `tests/test_install.py::test_move_renames_without_redirect_and_rewrites_relations` asserts the renamed slug appears as a block-style list item under `advances:` in the parent card (matching the documented convention in CLAUDE.md), not as inline `[renamed-card]`
  - [ ] The original child slug still must NOT appear anywhere in the parent's README (the existing `assertNotIn("child-card", parent_readme)` invariant is preserved)
  - [ ] `uv run python -m unittest discover -s tests` passes locally on Python 3.11
  - [ ] Pre-commit `goc validate` passes
worker: {who: Rodja Trappe, where: main}
---

# Test asserts pre-block-style inline `advances` format

## Why

The card `emit-advances-and-advanced-by-as-block-style-yaml-lists`
(closed 2026-05-07) switched the frontmatter emitter to render
`advances` and `advanced_by` as block-style YAML when non-empty.
That card's DoD covered the emitter, mutator, schema example, and
deck-wide migration, but the regression test
`test_move_renames_without_redirect_and_rewrites_relations` still
asserts the **inline** form:

```python
self.assertIn("advances: [renamed-card]", parent_readme)
```

The actual frontmatter the emitter now writes is:

```yaml
advances:
  - renamed-card
```

So the assertion fails. CI has been red on every push since
26bfce0 (the first push after the emitter switch landed).

## Fix

Update the assertion in `tests/test_install.py` to match the
documented format. Use a string fragment robust to surrounding
whitespace:

```python
self.assertIn("advances:\n  - renamed-card\n", parent_readme)
```

The companion `assertNotIn("child-card", parent_readme)` invariant
keeps catching stale slug leaks.

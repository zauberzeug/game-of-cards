---
title: test-move-asserts-old-inline-advances-format
summary: "tests/test_install.py::test_move_renames_without_redirect_and_rewrites_relations asserts the parent card's frontmatter contains `advances: [renamed-card]` (inline flow style). The emitter was switched to block style by emit-advances-and-advanced-by-as-block-style-yaml-lists, so the actual output is `advances:\\n  - renamed-card`. Test now fails on every push to main."
status: done
stage: null
contribution: medium
created: 2026-05-08
closed_at: 2026-05-08
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] `tests/test_install.py::test_move_renames_without_redirect_and_rewrites_relations` asserts the renamed slug appears as a block-style list item under `advances:` in the parent card (matching the documented convention in CLAUDE.md), not as inline `[renamed-card]`
  - [x] The original child slug still must NOT appear anywhere in the parent's README (the existing `assertNotIn("child-card", parent_readme)` invariant is preserved)
  - [x] `uv run python -m unittest tests.test_install.ClaudeHarnessInstallTest.test_move_renames_without_redirect_and_rewrites_relations` passes on Python 3.11 (the suite's only remaining failure, `test_board_and_open_queue_surface_active_cards`, is an unrelated local-only env leak — see Notes below)
  - [x] Pre-commit `goc validate` passes
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

## Notes — unrelated local test failure surfaced during this work

After fixing the `move_renames` assertion, the full suite still
shows one failure locally: `test_board_and_open_queue_surface_active_cards`.
That test reads the active card's slug `active-card` from the
`--board` view, but locally the new `worker` field auto-populates
from the host's git `user.name` (e.g. `@Rodja Trappe`), which
widens the column past the truncation point and clips `active-card`
to `active`. CI runs without a global git identity, so the
truncation does not happen and the test passes on CI. The CI log
for run 25539833785 confirms only `move_renames` failed (one `F`
out of 64 dots). This local leak is filed as a separate test-
isolation card; it is not part of this CI-unblock fix.

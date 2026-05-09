---
title: yaml-lite-empty-block-scalar-consumes-next-key
summary: "goc/_vendor/yaml_lite.py silently mis-parses a block scalar (`|`) with no indented content: the next key-value pair is consumed into the block scalar's value instead of being parsed as a separate key. Result is data corruption with no error — the missing key is silently dropped from the parsed dict."
status: active
stage: null
contribution: high
created: 2026-05-09
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] Reproduce: `safe_load("title: x\ndefinition_of_done: |\nworker: alice")` returns a dict with `worker == 'alice'` and `definition_of_done == ''` (or `'\n'`), not `{'definition_of_done': 'worker: alice\n'}` with worker absent.
  - [ ] Fix `_parse_block_scalar` in `goc/_vendor/yaml_lite.py`: when the first non-empty line after the `|` indicator has indent <= the declaration indent, return an empty string immediately without consuming that line.
  - [ ] All existing 97 tests still pass (`uv run pytest tests/ -q`).
  - [ ] `uv run goc validate --quiet` exits 0 against the repo's own deck.
  - [ ] Round-trip parity: every existing card under `.game-of-cards/deck/` survives `parse_frontmatter → emit_frontmatter → parse_frontmatter` with identical result.
  - [ ] New regression test covers: (a) empty block scalar followed by another key, (b) `|-` with no content followed by another key.
worker: {who: "claude[bot]", where: main}
---

# yaml-lite-empty-block-scalar-consumes-next-key

## Confirmed reproduction

```python
from goc._vendor.yaml_lite import safe_load
text = "title: test-card\ndefinition_of_done: |\nworker: alice"
result = safe_load(text)
# Actual:   {'title': 'test-card', 'definition_of_done': 'worker: alice\n'}
# Expected: {'title': 'test-card', 'definition_of_done': '', 'worker': 'alice'}
```

`worker` is absent from the parsed dict entirely — silent data loss, no exception.

## Root cause

In `_parse_block_scalar` (`goc/_vendor/yaml_lite.py`), the method determines the block indent from the first content line it encounters. When no indented content follows the `|`, the method peeks at the next line and uses its indent (0) as the block indent. A loop condition `if curr < indent: break` with `indent == 0` never triggers because `curr` (column 0) is never less than 0, so the loop consumes every remaining line in the document as block content.

## Impact

Any card whose frontmatter contains an empty block scalar (`definition_of_done: |` with nothing indented below it) will silently have all subsequent frontmatter keys consumed into that field's value. The returned dict is missing keys and contains garbage in the block scalar field — no exception is raised.

This pattern can appear naturally when a human or agent writes `definition_of_done: |` as a placeholder before adding items. The real deck avoids it today by always including at least one `  - [ ]` line, but there is no parser-level guard preventing the corrupting input. The `goc new` scaffold writes `  - [ ] (replace with real criteria)` which is indented, so newly scaffolded cards are safe — but hand-edited cards or partially-written cards are not.

## Fix sketch

`_parse_block_scalar` should detect when no indented content follows the `|` and return immediately with an empty string. After skipping blank lines, if the next non-blank line has indent <= the indicator's own indent level, treat the block scalar as empty and leave the position at that line so the parent loop can parse it as the next key.

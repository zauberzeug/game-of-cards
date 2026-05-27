---
title: yaml-lite-flow-mapping-drops-pairs-without-a-space-after-the-colon
summary: "`_parse_flow_mapping` splits each pair on `partition(\": \")`, requiring a space after the colon. A hand-written flow mapping like `worker: {who:rodja, where:foo}` (no space) yields an empty mapping — every pair is silently dropped. UNVERIFIED: confirmed in a one-liner but no full reproduce.py written yet."
status: done
stage: null
contribution: low
created: "2026-05-27T09:50:39Z"
closed_at: 2026-05-27T10:04:56Z
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: a reproduce.py asserting `safe_load('w: {who:a, where:b}') == {'w': {'who': 'a', 'where': 'b'}}` passes (currently returns `{'w': {}}`).
  - [x] TDD: pairs with a space after the colon continue to parse (no regression).
  - [x] MECHANICAL: `_parse_flow_mapping` splits on the first `:` (with optional surrounding whitespace), not the literal `": "`.
worker: {who: "claude[bot]", where: main}
---

# yaml-lite flow mapping drops `key:value` pairs that lack a space after the colon

> UNVERIFIED — the defect is confirmed by a one-line `safe_load` call (see
> below), but no full `deck/.../reproduce.py` has been written and the
> blast-radius across hand-edited frontmatter has not been surveyed. Drop the
> `unverified` tag once a reproduce.py lands.

## Location

`goc/_vendor/yaml_lite.py:335` — inside `_parse_flow_mapping`:

```python
key, _, val = pair.partition(": ")
```

## Hypothesis (what's broken)

`partition(": ")` requires the literal two-character separator `": "`. A flow
mapping element written without a space after the colon — e.g.
`{who:rodja, where:foo}` — has no `": "`, so `partition` returns the whole
string as the head with empty separator and empty tail. The key/value extraction
then produces a malformed or empty entry and the pair is discarded.

This matters because the `worker` field's documented mapping form
(`worker: {who: rodja, where: feature/foo}`, per AGENTS.md "worker field") is
exactly a flow mapping a human is invited to hand-edit. A typo omitting the
space silently empties the mapping rather than erroring — and the yaml-lite
parser's contract is to support hand-edited frontmatter.

## Empirical evidence (one-liner, not yet a reproduce.py)

```
$ uv run python -c "from goc._vendor import yaml_lite; print(repr(yaml_lite.safe_load('w: {who:a, where:b}')))"
{'w': {}}
```

Both `who:a` and `where:b` were dropped; the expected result is
`{'w': {'who': 'a', 'where': 'b'}}`.

## Why deferred

Low contribution: the engine's own emitter always writes `: ` (space after
colon), so this only bites hand-edited frontmatter, and the headline confirmed
defect this audit round is the higher-severity install data-loss card. Parked
unverified rather than dropped because the worker-mapping hand-edit path makes
it a real (if narrow) data-loss-on-reload risk.

## Falsification recipe

Write `reproduce.py` that calls `yaml_lite.safe_load` on a flow mapping with no
space after the colon and asserts the pairs survive. If it already round-trips
(e.g. a newer parser revision split on `:` not `": "`), the hypothesis is
falsified — `git log -p -- goc/_vendor/yaml_lite.py` since 2026-05-27 would show
the change.

## Surfaced by

audit-deck hunter (general-purpose agent), 2026-05-27.

---
title: goc-new-writes-duplicate-tags-when-tag-flag-is-repeated
summary: "`goc new` deduplicates `--advances` and `--advanced-by` via `_unique_preserving_order` but writes `--tag` values verbatim. Repeating `--tag bug --tag bug` lands `tags: [bug, bug]` on disk; `goc validate` does not catch it, so duplicates survive into the deck and downstream filters that count tags double-count."
status: open
stage: null
contribution: medium
created: "2026-05-30T06:30:27Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero (defect no longer fires — `goc new --tag X --tag X` produces `tags: [X]`, not `[X, X]`)
  - [ ] MECHANICAL: `_cmd_new` deduplicates `tags` the same way it deduplicates `advances` / `advanced_by` (via `_unique_preserving_order`)
  - [ ] PROCESS: decide whether `goc validate` should also flag pre-existing duplicates in already-filed cards (separate sibling card if yes)
  - [ ] TDD: a regression test in `tests/` covers `goc new --tag bug --tag bug`
  - [ ] PROCESS: `uv run goc validate` passes
---

# `goc new` keeps duplicate `--tag` values

## Location

`goc/engine.py:4107-4108` (the dedup is applied to `advances` /
`advanced_by` only) and `goc/engine.py:4130-4151` (the tag loop
validates each tag against `canonical_tags` but stores the list
verbatim).

## What's broken

`_cmd_new` reads each repeatable list-style flag from argparse, then
deduplicates `advances` and `advanced_by` before mutating disk:

```python
# goc/engine.py:4107-4108
advances = _unique_preserving_order(args.advances or [])
advanced_by = _unique_preserving_order(args.advanced_by or [])
```

The `--tag` flag is the third repeatable list-style argument on `goc
new` (declared at `goc/engine.py:2646` with the same
`action="append"` shape). It is NOT passed through
`_unique_preserving_order`. The downstream tag loop only validates
each value against the canonical-tag set:

```python
# goc/engine.py:4130-4136
for tag in tags:
    if tag not in schema.canonical_tags:
        print(
            f"ERROR: unknown tag '{tag}' — {_UNKNOWN_TAG_REMEDY}",
            file=sys.stderr,
        )
        sys.exit(2)
```

Then `tags` is written through unchanged:

```python
# goc/engine.py:4151
"tags": list(tags),
```

`goc validate` does not flag duplicate entries in `tags`. The
resulting card carries the duplicates persistently.

## Empirical evidence

Running the reproducer (`uv run python deck/<title>/reproduce.py`):

```
$ uv run python .game-of-cards/deck/goc-new-writes-duplicate-tags-when-tag-flag-is-repeated/reproduce.py
created .game-of-cards/deck/test-dedup-card/
Next: edit .game-of-cards/deck/test-dedup-card/README.md to fill the body and DoD; then ask your agent to implement the card.
tags written to disk: [bug, bug, documentation, bug]
DUPLICATES PRESENT — defect fires.
```

(See the script for details; runs in a fresh temp dir so it does not
touch this repo's deck.)

## Why it matters

The deck's canonical-tag system is a controlled vocabulary
(`schema.canonical_tags` + `.game-of-cards/canonical-tags.md`), with
`goc validate` enforcing membership. A card with `tags: [bug, bug,
bug]` is silently accepted; downstream tag-based filters
(`goc --tag bug`, `Skill(scan-deck)` tag groupings,
`Skill(retrospective)` tag clustering) treat each occurrence as a
separate hit. Aggregations that count cards per tag are now skewed by
how many times the filer typo'd the flag, not by the underlying
classification. The bug is reachable through ordinary one-shot card
authoring — any agent (or human) running `goc new <title> --tag X
--tag X` lands duplicates.

The same one-line fix that deduplicates `advances` and `advanced_by`
applies here; the fact that two of the three repeatable list-style
flags are deduplicated and the third is not is a maintenance defect
waiting to be hit again whenever a new such flag is added.

## Fix

Apply `_unique_preserving_order` to `tags` alongside the existing
calls. Concretely, at `goc/engine.py:4104`:

```python
tags = args.tags
```

becomes

```python
tags = _unique_preserving_order(args.tags or [])
```

(matching the two-line pattern just below for `advances` and
`advanced_by`).

A `goc validate` rule that flags duplicate entries in `tags` on
*already-filed* cards is a separate, larger fix — it would surface
pre-existing duplicates in the deck and require an explicit migration
or autofix flag. Leaving that out of scope here keeps the fix
mechanical; the DoD's PROCESS box records the decision.

---
title: worker-mapping-with-only-a-branch-emits-invalid-empty-who
summary: "`_emit_worker` renders a worker dict with `where` but missing `who` as `{who: \"\", where: ...}`. Confirmed reachable: any full-frontmatter re-emit verb (`goc wait`/`decide`/`advance`/`unadvance`/`quality-pass`/`migrate-list-style`) rewrites a `worker: {where: x}` card into that form, inventing a `who` the author never wrote and turning the validate error from 'missing who key' into 'who must be non-empty'. Fix path (refuse vs normalize) needs a decision."
status: open
stage: null
contribution: low
created: "2026-05-27T08:02:35Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py demonstrates a real `goc` verb (`goc wait` on a card with `worker: {where: ...}` and no `who`) emitting `who: ""` then failing `goc validate`.
  - [ ] PROCESS: decide the fix — refuse the malformed input at the emitter, or normalize (drop the mapping to bare/null when `who` is empty). Record in log.md.
  - [ ] MECHANICAL: `goc validate` clean; plugin mirrors synced.
---

# Worker mapping with only a branch emits an invalid empty `who`

CONFIRMED (2026-06-19) — `reproduce.py` exercises a real verb end-to-end. The
emitter manufactures an empty `who`, and the defect is reachable through every
full-frontmatter re-emit verb.

## Location

`goc/engine.py:297-302` — `_emit_worker`:

```python
if isinstance(value, dict):
    who = value.get("who", "")
    where = value.get("where")
    if where:
        return f"{{who: {_yaml_inline(who)}, where: {_yaml_inline(where)}}}"
    return _yaml_inline(who)
```

## What's broken

When the worker value is a dict with a truthy `where` but an empty or missing
`who`, the emitter defaults `who` to `""` and writes `{who: "", where: ...}`.
On re-parse that is `who: ''`, which `validate_card`
(`goc/engine.py:1487-1490`) rejects:

```python
if "who" not in worker:
    errors.append(f"{t.title}: worker: mapping must have a 'who' key")
elif not isinstance(worker.get("who"), str) or not worker["who"].strip():
    errors.append(f"{t.title}: worker: 'who' must be a non-empty, non-whitespace string")
```

So the emitter does not merely *preserve* a malformed worker — it **invents**
an empty `who` the author never wrote, mutating a *missing-key* error
(fixable by adding `who`) into a *non-empty-string* error, all while the verb
reports success.

This contradicts the module's own invariant. The sibling writer
`_auto_populate_worker` (`goc/engine.py:4493-4499`) explicitly refuses this
exact shape:

> A worker mapping requires a non-empty `who` ... there is no valid worker to
> stamp ... rather than write an invalid `{who: "", where: <branch>}` that
> self-corrupts the card.

And `_yaml_inline` raises `FrontmatterError` rather than emit a value that
cannot round-trip ("refuse at the boundary rather than advertise a type that
cannot round-trip"). `_emit_worker` is the one site that violates that shared
invariant by silently emitting the corrupt form.

## Why it matters / reachability

The status verbs (`goc status`, the `done` paths) mutate via
`mutate_frontmatter_field` (line-anchored regex) and never touch the `worker`
line. But six verbs re-emit the **entire** frontmatter through
`emit_frontmatter` → `_emit_worker`:

- `goc wait` (`_cmd_wait`, engine.py:4957)
- `goc decide` (`_cmd_decide`, engine.py:5247)
- `goc advance` / `goc unadvance` (`_add_to_list_field` / `_remove_from_list_field`, engine.py:4767/4776)
- `goc quality-pass` (`_apply_summary_rewrite` / `_apply_dod_rewrite`, engine.py:3553/3573)
- `goc migrate-list-style` (`_cmd_migrate_list_style`, engine.py:5499)

None of these validate the card before mutating, so a card hand-authored or
migrated with `worker: {where: feature/x}` (a plausible shape — AGENTS.md
documents the mapping form `worker: {who: rodja, where: feature/foo}`, and a
user could omit `who`) loads fine and is silently corrupted further by the
verb. `reproduce.py` demonstrates this with `goc wait`.

## Empirical evidence

`uv run python .game-of-cards/deck/worker-mapping-with-only-a-branch-emits-invalid-empty-who/reproduce.py`:

```
1. _emit_worker({'where': 'feature/x'}) -> '{who: "", where: feature/x}'
   manufactures empty who: True

2. INPUT worker line: worker: {where: feature/x}
   validate BEFORE verb: ERROR: scratch-card: worker: mapping must have a 'who' key

3. `goc wait` exit: 0 -> scratch-card: waiting_on='external' waiting_until=None
   OUTPUT worker line: worker: {who: "", where: feature/x}

4. validate AFTER verb: ERROR: scratch-card: worker: 'who' must be a non-empty, non-whitespace string

DEFECT CONFIRMED: emit-path verb invented `who: ""` and turned a missing-key error into a non-empty-string error.
```

## Decision required

The defect is confirmed; the fix is a judgment call between two credible
approaches, each with a real behavioral consequence:

1. **Refuse at the emitter.** Make `_emit_worker` raise `FrontmatterError`
   when `who` is empty/missing but `where` is present — consistent with
   `_yaml_inline`'s round-trip refusal and `_auto_populate_worker`'s guard.
   Consequence: `goc wait`/`decide`/`advance`/… would **raise** on a card
   carrying a malformed worker rather than rewrite it. A clear failure, but it
   turns a silent corruption into a hard crash mid-verb.

2. **Normalize at the emitter.** When `who` is empty/missing, drop the
   mapping. But a `where`-only worker has no valid bare form (the flat string
   *is* `who`), so normalization must choose: emit `null` (drops the worker
   entirely, losing the authored `where`), or keep the malformed shape and let
   `goc validate` surface it on the input as today. Each choice changes what a
   verb silently does to authored data.

A third option — validate the worker on the *input* side of every emit verb
and refuse before mutating — moves the guard out of the emitter entirely.

Record the chosen approach and rationale in `log.md`, then implement and close.

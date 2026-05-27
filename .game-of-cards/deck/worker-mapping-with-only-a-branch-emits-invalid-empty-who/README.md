---
title: worker-mapping-with-only-a-branch-emits-invalid-empty-who
summary: "UNVERIFIED. `_emit_worker` renders a worker dict that has `where` but an empty/missing `who` as `{who: \"\", where: ...}`, which round-trips to `who: ''` — a value `validate_card` rejects as 'who must be a non-empty string'. If reachable via an emit-path verb, a card could self-corrupt into a validate failure. Needs a reproduce.py proving a real `goc` verb produces this state."
status: open
stage: null
contribution: low
created: "2026-05-27T08:02:35Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, unverified]
definition_of_done: |
  - [ ] TDD: reproduce.py demonstrates a real `goc` verb (e.g. `goc status`/`goc advance` on a card with `worker: {where: ...}` and no `who`) emitting `who: ""` then failing `goc validate`.
  - [ ] PROCESS: decide the fix — refuse the malformed input at the emitter, or normalize (drop the mapping to bare/null when `who` is empty). Record in log.md.
  - [ ] MECHANICAL: `goc validate` clean; plugin mirrors synced.
---

# Worker mapping with only a branch emits an invalid empty `who`

UNVERIFIED — surfaced by an audit hunter, cited code read and confirmed
present, but no `reproduce.py` exercised this round. Park with a falsification
recipe.

## Hypothesis (file:line)

`goc/engine.py:270-275`:

```python
if isinstance(value, dict):
    who = value.get("who", "")
    where = value.get("where")
    if where:
        return f"{{who: {_yaml_inline(who)}, where: {_yaml_inline(where)}}}"
    return _yaml_inline(who)
```

When the worker value is a dict with a truthy `where` but an empty or missing
`who`, the emitter produces `{who: "", where: ...}`. On re-parse that is
`who: ''`, which `validate_card` rejects (`worker: 'who' must be a non-empty
string`). So an emit-path mutation on such a card would manufacture a
validate failure rather than refusing or normalizing the input.

## Why deferred

Reachability is unconfirmed: it depends on whether any real `goc` verb can
arrive at `_emit_worker` with a `{where: ...}`-only dict. `goc status <t>
active` auto-populates `who`, and a hand-authored `worker: {where: x}` may be
rejected by `validate_card` on the *input* side before any emit ever runs. The
defect is only real if there is a code path that (a) accepts such a worker
value and (b) re-emits it. One filed card consumed this audit round's
verification budget.

## Falsification recipe

1. Author a card with `worker: {where: feature/x}` (no `who`).
2. If `goc validate` already rejects it on input, the emitter contradiction is
   unreachable → disprove.
3. If it is accepted, run an emit-path verb (`goc advance` / `goc status`) and
   re-`goc validate`; confirm the round-trip yields `who: ''` and a validate
   error. If so, promote (drop `unverified`, add a working `reproduce.py`).

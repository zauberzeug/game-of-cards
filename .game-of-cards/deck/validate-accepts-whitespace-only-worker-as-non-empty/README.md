---
title: validate-accepts-whitespace-only-worker-as-non-empty
summary: "`goc validate` accepts `worker: \" \"` (a whitespace-only string) and `worker: {who: \" \"}` (whitespace-only `who` in the mapping form) as if they were non-empty. The validator predicate `not worker` / `not worker[\"who\"]` catches `\"\"` but not `\" \"`, so the validator violates its own stated rule (\"must not be an empty string\"). Reachable via `goc new --worker \" \"` and `goc status <t> active --worker-who \" \"`."
status: active
stage: null
contribution: low
created: "2026-05-30T13:02:01Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — `goc validate` rejects both `worker: " "` and `worker: {who: " "}` with a non-zero exit and an error message naming the offending card.
  - [ ] TDD: regression test added under `tests/` covering both the bare-string and mapping forms of the whitespace-only worker check.
  - [ ] MECHANICAL: the validator predicate in `goc/engine.py` rejects strings that are non-empty but consist only of whitespace (use `not worker.strip()` / `not worker["who"].strip()`).
  - [ ] MECHANICAL: `uv run goc validate` clean on this repo's own deck after the fix; plugin mirrors synced.
worker: {who: "claude[bot]", where: main}
---

# `goc validate` accepts whitespace-only `worker` as non-empty

## Location

`goc/engine.py:1259-1268` — the worker-field branch of `validate_card`.

## What's broken

The validator intends to reject empty worker values — both the bare-string
form and the mapping form's `who` key. The error messages say so:

```python
worker = fm.get("worker")
if worker is not None:
    if isinstance(worker, str):
        if not worker:
            errors.append(f"{t.title}: worker: must not be an empty string")
    elif isinstance(worker, dict):
        if "who" not in worker:
            errors.append(f"{t.title}: worker: mapping must have a 'who' key")
        elif not isinstance(worker.get("who"), str) or not worker["who"]:
            errors.append(f"{t.title}: worker: 'who' must be a non-empty string")
```

But `not worker` and `not worker["who"]` only catch the literal empty string
`""`. A whitespace-only string like `" "` is truthy in Python, so it slips
through — even though it carries zero semantic content and is plainly what
the rule is meant to block.

## Empirical evidence

Reproduction in a scratch repo (full transcript in `reproduce.py`):

```text
$ goc new ws-bare --contribution medium --gate none --worker " "
created .game-of-cards/deck/ws-bare/

$ grep '^worker:' .game-of-cards/deck/ws-bare/README.md
worker: " "

$ goc validate
WARN UNTAGGED_DOD_ITEM ws-bare: 1 DoD item(s) lack a method tag (...)
OK  ws-bare
```

`OK ws-bare` is the bug: the validator passed a card whose `worker` value
is semantically empty.

The mapping form is reachable the same way via `goc status <t> active
--worker-who " "`, which writes `worker: {who: " ", where: <branch>}` and
likewise passes `goc validate`.

## Why it matters

The validator is the contract surface for the schema. Two CLI entry points
write the offending shape directly:

- `goc/engine.py:_cmd_new` — `if worker: fm["worker"] = worker` treats
  `" "` as truthy and persists it.
- `goc/engine.py:_auto_populate_worker` — emits `worker: {who: " ",
  where: ...}` when `goc status <t> active --worker-who " "` is invoked.

Worker is the field that drives `goc --worker <X>` filters and the
runner-specific queue views described in AGENTS.md. A whitespace-only
worker silently matches no filter usefully but still occupies the field,
giving the impression a card is claimed when it carries no real
attribution. Low blast radius (descriptive metadata, no crashes), but the
validator quietly contradicts its own stated rule — a small but real
api-contract regression.

## Fix

In `goc/engine.py:1259-1268`, normalize before the emptiness check:

```python
if isinstance(worker, str):
    if not worker.strip():
        errors.append(f"{t.title}: worker: must not be empty or whitespace-only")
elif isinstance(worker, dict):
    ...
    elif not isinstance(worker.get("who"), str) or not worker["who"].strip():
        errors.append(f"{t.title}: worker: 'who' must be a non-empty, non-whitespace string")
```

The matching authoring-time guards in `_cmd_new` and `_auto_populate_worker`
should likewise refuse a whitespace-only `--worker` / `--worker-who` value
so the bad input never lands on disk in the first place — but the
validator is the gate the DoD targets.

## Cross-references

- [worker-mapping-with-only-a-branch-emits-invalid-empty-who](../worker-mapping-with-only-a-branch-emits-invalid-empty-who/)
  — sibling defect about the *emitter* producing `who: ""` from a
  branch-only mapping (the validator does reject `""`). This card is the
  inverse gap: the validator under-rejects whitespace.

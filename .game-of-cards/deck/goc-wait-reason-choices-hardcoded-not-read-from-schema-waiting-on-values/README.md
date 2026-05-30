---
title: goc-wait-reason-choices-hardcoded-not-read-from-schema-waiting-on-values
summary: "`p_wait.add_argument(\"--reason\", choices=[\"external\", \"resource\", \"deferred\"], …)` at `engine.py:2662` hardcodes the same list that `schema.yaml:27` already defines as `waiting_on_values`. Every other enum-typed CLI arg in `_build_parser` reads from `schema.*` (contribution, human_gate, status). The validator at `_cmd_wait` does read `schema.waiting_on_values`. Adding a new value to schema.yaml would silently fail at the argparse layer while the validator accepted it — a schema-source-of-truth drift that the project's architecture explicitly tries to prevent."
status: active
stage: null
contribution: low
created: "2026-05-30T09:41:52Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, unverified]
definition_of_done: |
  - [ ] MECHANICAL: `engine.py:2662` reads from `schema.waiting_on_values` (matching the pattern at `engine.py:2643-2645`).
  - [ ] TDD: a regression test asserts the `--reason` argparse choices equal `schema.waiting_on_values`.
  - [ ] PROCESS: `uv run goc validate` is clean.
worker: {who: "claude[bot]", where: main}
---

# `goc wait --reason` choices are hardcoded instead of read from schema.yaml

## Hypothesis (file:line)

`goc/engine.py:2662`:

```python
p_wait.add_argument("--reason", choices=["external", "resource", "deferred"], default=None, …)
```

`goc/schema.yaml:27`:

```yaml
waiting_on_values: [external, resource, deferred]
```

Adjacent enum-typed args in the same `_build_parser` already read from
the schema:

```python
# engine.py:2643-2645
p_new.add_argument("--contribution", choices=schema.contribution_values, …)
p_new.add_argument("--gate", choices=schema.human_gate_values, default=schema.human_gate_default)
```

And `_cmd_wait`'s own validation (further down the file) reads
`schema.waiting_on_values` — so the argparse layer and the runtime
validator already disagree about where the source of truth lives. If
someone adds a fourth `waiting_on` value to `schema.yaml`, the
validator would accept a card carrying it, but `goc wait --reason
<new-value>` would be rejected by argparse before the new value
reached the validator.

## Why deferred (unverified)

The defect is structural (single source-of-truth violation), trivial
to fix (one-line edit to mirror the adjacent pattern), and the
reachability path is direct — but no `reproduce.py` budget this round.
Filing as `unverified` so it can be promoted when someone has time to
write the regression test asserting the argparse choices stay
schema-driven.

## Falsification recipe

1. Add `extra-wait-reason` to `schema.yaml:27` `waiting_on_values`.
2. `uv run goc wait some-card --reason extra-wait-reason` — observe the
   argparse rejection.
3. Hand-edit a card to add `waiting_on: extra-wait-reason`, run
   `uv run goc validate` — observe acceptance.
4. The two layers disagree → defect confirmed.

Then revert the schema edit.

## Fix

```diff
-    p_wait.add_argument("--reason", choices=["external", "resource", "deferred"], default=None,
+    p_wait.add_argument("--reason", choices=schema.waiting_on_values, default=None,
                         help="Exogenous wait reason. Composes with --until.")
```

## Surfaced by

`audit-deck` round, 2026-05-30, `general-purpose` hunter candidate #3
of 3.

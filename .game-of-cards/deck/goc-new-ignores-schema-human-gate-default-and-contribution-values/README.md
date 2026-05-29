---
title: goc-new-ignores-schema-human-gate-default-and-contribution-values
summary: "`goc new` hardcoded the argparse defaults `--gate default=\"decision\"` and `--contribution choices=[...]` instead of reading `schema.human_gate_default` / `schema.contribution_values`, so the schema gate-default was dead config — a repo that changed `human_gate_default` saw `goc new` silently ignore it. Fixed: `_build_parser` now loads the schema and derives the `new` subparser's gate default and contribution choices from it."
status: done
stage: null
contribution: low
created: "2026-05-26T22:25:59Z"
closed_at: "2026-05-26T23:15:21Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] EMPIRICAL: confirm `human_gate_default` is read only at the `Schema` constructor and never by the new-card path (`grep` + trace `_cmd_new`); record verdict in log.md either way
  - [x] TDD: editing `schema.yaml` to `human_gate_default: none` and running `goc new foo-bar` (with no `--gate`) emits `human_gate: none`, not `decision`
  - [x] MECHANICAL: `goc new` derives the `--gate` default from `schema.human_gate_default` and the `--contribution` choices from `schema.contribution_values`, rather than hardcoded literals
  - [x] PROCESS: drop the `unverified` tag once the behavior is confirmed and a fix path chosen; `uv run goc validate` clean
worker: {who: "claude[bot]", where: main}
---

# goc-new-ignores-schema-human-gate-default-and-contribution-values

> **Status: confirmed and fixed (2026-05-26).** Traced `_cmd_new` end to
> end — it reads `args.gate` / `args.contribution` straight from the
> argparse defaults; the schema fields were never consulted on the
> new-card path. `_build_parser` now loads the schema and derives the
> `new` subparser's `--gate` default from `schema.human_gate_default` and
> the `--contribution` choices from `schema.contribution_values`.

## Hypothesis

`schema.yaml` treats the new-card gate default as configurable
(`human_gate_default`), and the `card-schema` skill documents it as "the
default for new cards created via `goc new`." But `goc new` hardcodes the
argparse `default="decision"`, so the schema field is never consulted —
dead config that would silently diverge from a customized schema.

## Location (verbatim)

`goc/schema.yaml:26`:

```yaml
human_gate_default: decision
```

Loaded at `goc/engine.py:380`:

```python
human_gate_default=fm["human_gate_default"],
```

But the new-card argument is a hardcoded literal — `goc/engine.py:2235`:

```python
p_new.add_argument("--gate", choices=["none", "decision", "session"], default="decision")
```

and `goc/engine.py:2234` similarly hardcodes `--contribution`
`default="medium"` with literal `choices=["high","medium","low"]` rather
than `schema.contribution_values`.

## Why deferred

Low severity — the hardcoded literal happens to equal the shipped schema
default, so there is no user-visible drift in this repo today. It only
bites a consuming repo (or a future schema bump) that changes
`human_gate_default`. Parked rather than fixed blind because the right fix
(thread `schema` into `_build_parser`/`_cmd_new`, or apply the default in
`_cmd_new` after parsing) needs a small design choice.

## Falsification recipe

1. `grep -n "human_gate_default" goc/engine.py` → expect it appears only at
   the `Schema` constructor (line ~380), never inside `_cmd_new`.
2. Set `human_gate_default: none` in `schema.yaml`, run `goc new foo-bar`
   with no `--gate`, inspect the emitted frontmatter.
   - **Predict (defect):** `human_gate: decision`.
   - **Predict (fixed):** `human_gate: none`.

If `_cmd_new` is found to already consult `schema.human_gate_default`
somewhere, this card is disproved.

Surfaced by a general-purpose audit hunter (doc/contract scope) on
2026-05-26.


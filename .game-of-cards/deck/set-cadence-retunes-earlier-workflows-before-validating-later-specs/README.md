---
title: set-cadence-retunes-earlier-workflows-before-validating-later-specs
summary: "scripts/set_cadence.py validates each interval spec inside `retune`, per workflow, inside the mutation loop — so `--pull 2h --audit 5h` rewrites pull-card.yml before discovering that `5h` is invalid, then prints an error and exits 2 with the workflow file already mutated. An operator who trusts the nonzero exit unknowingly commits or discards a retuned deck-mutating autonomous workflow. Fix: validate every requested spec via `interval_to_cron` before the retune loop."
status: active
stage: null
contribution: medium
created: "2026-07-17T01:07:16Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero (invalid later spec leaves ALL workflow files untouched and exit code is nonzero)
  - [ ] MECHANICAL: all requested specs are validated via `interval_to_cron` before the first `retune` call in `main` (scripts/set_cadence.py)
  - [ ] TDD: `uv run python -m unittest discover -s tests` passes (add a regression test if the suite covers set_cadence)
  - [ ] MECHANICAL: `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# set_cadence applies earlier workflow retunes before validating later specs

## Location

`scripts/set_cadence.py:247-252` (the mutation loop in `main`) and
`scripts/set_cadence.py:141` (`cron = interval_to_cron(spec, offset)` —
validation happens inside `retune`, after earlier loop iterations have
already called `path.write_text(text3)` at line 177).

## What's broken

```python
    for key, spec in requested.items():
        try:
            cron, changed = retune(repo_root, key, spec)
        except (ValueError, FileNotFoundError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
```

Interval-spec validation lives inside `retune` (`interval_to_cron` raises
`ValueError` on a bad spec), so it runs per workflow, mid-loop. The in-file
guard comment ("the file is only written after both guards pass",
scripts/set_cadence.py:149-151) makes each *file* write atomic, but there is
no cross-workflow pre-validation: with two requested changes where the
second spec is invalid, the first workflow is rewritten on disk before the
error surfaces.

## Empirical evidence

`reproduce.py` copies the script plus the real workflow files into a scratch
tree and runs `--pull 2h --audit 5h` (5 does not divide 24, so `5h` is
rejected):

```
exit code: 2 (stderr: error: '5h': hour interval must divide 24 ...)
pull-card.yml mutated despite failure exit: True
DEFECT CONFIRMED: command failed but left an earlier workflow retuned
```

## Why it matters

The retuned files are `.github/workflows/pull-card.yml` /
`audit-deck.yml` / `refine-deck.yml` — the autonomous deck-mutating
schedules. A failure exit conventionally means "nothing happened"; here the
operator (or the `tune-cadence` skill wrapping this script) sees exit 2,
retries or gives up, and either commits a half-applied cadence change with
the next unrelated commit or discards a change they never knew was made.
This is the inverse of the misleading-no-op-success family
([mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success](../mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success/)):
it reports failure while having mutated.

## Fix

Pre-validate every requested spec before the mutation loop in `main`
(offsets are known from `WORKFLOWS`):

```python
    for key, spec in requested.items():
        try:
            interval_to_cron(spec, WORKFLOWS[key][1])
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    for key, spec in requested.items():
        ...
```

`FileNotFoundError` from a missing workflow file can stay in the loop or be
pre-checked the same way; pre-checking both makes the command all-or-nothing.

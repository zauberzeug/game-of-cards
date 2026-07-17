---
title: set-cadence-retunes-earlier-workflows-before-validating-later-specs
summary: "scripts/set_cadence.py validated each interval spec inside `retune`, per workflow, inside the mutation loop — so `--pull 2h --audit 5h` rewrote pull-card.yml before discovering that `5h` is invalid, then printed an error and exited 2 with the workflow file already mutated. Fixed: `main` now dry-runs every requested retune (`retune(..., write=False)` — spec validation via `interval_to_cron`, file existence, managed-line guards) before the mutation loop, so a failure exit always means no workflow file changed."
status: done
stage: null
contribution: medium
created: "2026-07-17T01:07:16Z"
closed_at: "2026-07-17T01:24:55Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (invalid later spec leaves ALL workflow files untouched and exit code is nonzero)
  - [x] MECHANICAL: all requested specs are validated via `interval_to_cron` (inside the `retune(write=False)` dry-run pass) before the first mutating `retune` call in `main` (scripts/set_cadence.py)
  - [x] TDD: `uv run python -m unittest discover -s tests` passes (add a regression test if the suite covers set_cadence)
  - [x] MECHANICAL: `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# set_cadence applies earlier workflow retunes before validating later specs

> Fixed 2026-07-17: `main` dry-runs every requested retune before the first
> write; `--pull 2h --audit 5h` now exits 2 with all workflow files untouched.

## Location

`scripts/set_cadence.py` — the mutation loop in `main` and
`retune` (`cron = interval_to_cron(spec, offset)`), where spec validation
used to happen per workflow, after earlier loop iterations had already
called `path.write_text(...)`.

## What was broken

```python
    for key, spec in requested.items():
        try:
            cron, changed = retune(repo_root, key, spec)
        except (ValueError, FileNotFoundError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
```

Interval-spec validation lived inside `retune` (`interval_to_cron` raises
`ValueError` on a bad spec), so it ran per workflow, mid-loop. The in-file
guards made each *file* write atomic, but there was no cross-workflow
pre-validation: with two requested changes where the second spec was
invalid, the first workflow was rewritten on disk before the error
surfaced.

## Empirical evidence

`reproduce.py` copies the script plus the real workflow files into a scratch
tree and runs `--pull 2h --audit 5h` (5 does not divide 24, so `5h` is
rejected). Before the fix:

```
exit code: 2 (stderr: error: '5h': hour interval must divide 24 ...)
pull-card.yml mutated despite failure exit: True
DEFECT CONFIRMED: command failed but left an earlier workflow retuned
```

After the fix it prints `OK: failure exit left all workflow files untouched`
and exits 0.

## Why it mattered

The retuned files are `.github/workflows/pull-card.yml` /
`audit-deck.yml` / `refine-deck.yml` — the autonomous deck-mutating
schedules. A failure exit conventionally means "nothing happened"; here the
operator (or the `tune-cadence` skill wrapping this script) saw exit 2,
retried or gave up, and either committed a half-applied cadence change with
the next unrelated commit or discarded a change they never knew was made.
This is the inverse of the misleading-no-op-success family
([mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success](../mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success/)):
it reports failure while having mutated.

## Fix (implemented)

`retune` gained a `write: bool = True` keyword; `write=False` runs every
validation (spec via `interval_to_cron`, file existence, single-`cron`-line
and single-`# cadence`-marker guards) without touching the file. `main`
dry-runs every requested retune before the mutation loop:

```python
    # All-or-nothing: dry-run every requested retune (spec validation via
    # interval_to_cron, file existence, managed-line guards) before the
    # mutation loop, so a failure exit always means no workflow file changed.
    for key, spec in requested.items():
        try:
            retune(repo_root, key, spec, write=False)
        except (ValueError, FileNotFoundError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
```

This is strictly stronger than the originally proposed spec-only
pre-validation: a later workflow that fails the managed-line guards (e.g. a
hand-added second `- cron:` line) also aborts before the earlier workflow is
rewritten.

## Artifacts

- reproduce.py
- Regression tests: `tests/test_set_cadence.py` — `MainAllOrNothingTest`
  (invalid later spec, guard failure in a later workflow, valid-path apply)
  and `RetuneTest.test_dry_run_validates_without_writing`.

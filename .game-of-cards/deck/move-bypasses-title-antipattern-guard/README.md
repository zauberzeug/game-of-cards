---
title: move-bypasses-title-antipattern-guard
summary: "`goc new` rejects engineer-jargon title antipatterns such as `bug-123-*`, but `goc move` accepts the same bad slug and `goc validate` stays green. Retitling can therefore create titles the filing path forbids."
status: active
stage: null
contribution: medium
created: 2026-05-04
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] `uv run python deck/move-bypasses-title-antipattern-guard/reproduce.py` exits zero
  - [ ] `goc move` applies the same title-antipattern guard as `goc new`
  - [ ] A deliberate bypass, if still needed for migrations, is explicit and named consistently with `--allow-jargon`
  - [ ] Regression coverage proves `bug-123-*`, `r88-*`, and camelCase retitle targets are rejected by default
---

# move-bypasses-title-antipattern-guard

## Location

- `goc/engine.py:1600`
- `goc/engine.py:1610`
- `goc/engine.py:1621`
- `goc/engine.py:1630`
- `goc/engine.py:1747`
- `goc/engine.py:1750`

## What's broken

The `new` command has an explicit title-antipattern guard:

```python
if not allow_jargon:
    antipatterns_hit = _check_title_antipatterns(title)
    if antipatterns_hit:
        ...
        sys.exit(2)
```

The `move` command validates only the schema regex:

```python
if not re.match(schema.title_pattern, new_title):
    click.echo(f"ERROR: title {new_title!r} does not match {schema.title_pattern!r}", err=True)
    sys.exit(2)
```

So the same title shape that `goc new` rejects can enter the deck via
`goc move`.

## Empirical evidence

Current output from `uv run python deck/move-bypasses-title-antipattern-guard/reproduce.py`:

```text
create_good_exit=0
new_bad_exit=2
new_bad_stderr_first=ERROR: title 'bug-123-regression' contains engineer-jargon antipattern(s):
move_bad_exit=0
move_bad_stdout=good-card → bug-123-regression
validate_exit=0
validate_stderr=
defect present: move accepts a title that new rejects
```

## Why it matters

Title quality is a deck readability invariant, not just a filing-time
preference. `quality-pass` and `improve-deck` both use retitling to
repair old names; the retitle path should not be able to create new
engineer-jargon titles that `new` would refuse.

## Fix

Apply `_check_title_antipatterns(new_title)` in `move()` by default.
If migration tooling still needs a bypass, add an explicit
`--allow-jargon` option with the same warning semantics as `goc new`.

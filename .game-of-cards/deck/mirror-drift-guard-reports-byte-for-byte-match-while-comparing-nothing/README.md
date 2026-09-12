---
title: mirror-drift-guard-reports-byte-for-byte-match-while-comparing-nothing
summary: "scripts/sync_plugin_assets.py's __pycache__/.pyc exclusion substring-matches the ABSOLUTE path instead of the path's parts and suffix, so on any checkout whose directory name contains one of those fragments every source and destination item is skipped. --check then prints \"OK — byte-for-byte\" having compared nothing, and the pre-commit auto-sync stages nothing. The three sibling implementations of the identical exclusion all scope it correctly to .parts/.suffix."
status: active
stage: null
contribution: medium
created: "2026-09-10T04:51:50Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — `--check` reports drift for a corrupted mirror and a deleted hook on a checkout under a `.pyc`-containing path
  - [ ] TDD: a regression test pins `_skip` itself — the exclusion matches `__pycache__` components and `.pyc` suffixes, and does NOT match a benign ancestor directory named e.g. `.pycharm`
  - [ ] MECHANICAL: `_skip` scopes its test to `path.parts` / `path.suffix`, matching the three sibling sites (`scripts/port_skills_to_openclaw.py:240`, `goc/install.py:938`, `goc/install.py:1194`)
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` pass
worker: {who: "claude[bot]", where: main}
---

# The mirror drift guard reports a byte-for-byte match while comparing nothing

## Location

`scripts/sync_plugin_assets.py:221` and `:235-237`:

```python
_SKIP_FRAGMENTS = ("__pycache__", ".pyc")


def _skip(path: Path) -> bool:
    s = str(path)
    return any(frag in s for frag in _SKIP_FRAGMENTS)
```

`_skip` is called at ten sites in the walk (`:265`, `:280`, `:323`, `:375`,
`:385`, `:410`, `:431`, `:449`, `:501`, …), on absolute source and destination
paths.

## What's broken

The exclusion is meant to skip compiled-Python artifacts: `__pycache__`
directories and `.pyc` files. It tests the fragments against `str(path)` of the
**absolute** path, so it also matches any ancestor directory whose name happens
to contain one — `.pycharm/`, `~/dev/.pyc-cache/`, a branch checkout named
`fix-pyc-handling`, and so on.

When that happens, every item the walk offers is "skipped". The sync copies
nothing and the guard compares nothing — and reports the empty comparison as
success:

```
OK — plugin payloads + dogfood self-host copies match goc/ and goc/templates/ byte-for-byte.
```

The three sibling implementations of the identical exclusion all scope it to
path components and suffix, which is the correct form:

```python
scripts/port_skills_to_openclaw.py:240
    if "__pycache__" in asset.parts or asset.suffix == ".pyc":

goc/install.py:938  /  :1194  /  :1241
    if asset.is_dir() or "__pycache__" in asset.parts:
```

## Empirical evidence

`uv run python .game-of-cards/deck/mirror-drift-guard-reports-byte-for-byte-match-while-comparing-nothing/reproduce.py`
— repo exported under `.pycharm/checkout`, one mirrored skill corrupted and one
mirrored hook deleted:

```
baseline   : exit=0 :: OK — plugin payloads + dogfood self-host copies match goc/ and goc/templates/ byte-for-byte.
after drift: exit=0 :: OK — plugin payloads + dogfood self-host copies match goc/ and goc/templates/ byte-for-byte.
sync run   : (no output — total no-op)
after sync : content still drifted=True, hook still missing=True

[FAIL] --check reported success with a corrupted mirror and a deleted hook: the guard compared nothing.
```

`--check` exits 0 both before and after the corruption, and the plain sync run
prints no `synced N file(s)` line at all.

## Why it matters

AGENTS.md makes this script the load-bearing guard for four mirror trees:

> CI runs `python scripts/sync_plugin_assets.py --check` and fails the build on
> any drift, so editing only `.claude/skills/...` or `.codex/skills/...` is now
> CI-detectable (it gets overwritten by the next pre-commit pass).

Both halves of that guarantee fail together on an affected checkout: the
pre-commit hook stops regenerating the mirrors, so a template edit ships without
its mirrors, and `--check` stays green so nothing surfaces it. The failure mode
is worse than a missing check, because the output actively asserts the payloads
match.

The trigger is a property of the *checkout path*, not the repo, which bounds
who is affected — GitHub Actions runners use `/home/runner/work/...`, so CI is
currently safe — but it also means the same commit passes for one contributor
and silently no-ops for another, with no signal distinguishing the two.

This is a sibling of
[sync-mechanisms-reimplement-orphan-pruning-and-drift-detection-and-keep-drifting](../sync-mechanisms-reimplement-orphan-pruning-and-drift-detection-and-keep-drifting/),
which catalogues the same script's duplicated walk logic. That umbrella is
scoped to orphan pruning and drift detection; the duplicated predicate here is
the exclusion filter, and the failure mode is a whole-guard no-op rather than a
retained orphan. Filed separately because the fix is a one-line scoping change
that needs no decision, where the umbrella needs one.

## Fix

`scripts/sync_plugin_assets.py:235-237` — scope the test to the path's own
components and suffix, as the three sibling sites already do:

```python
def _skip(path: Path) -> bool:
    return "__pycache__" in path.parts or path.suffix == ".pyc"
```

`_SKIP_FRAGMENTS` then has no remaining reader and goes with it. A regression
test should pin both directions: a `__pycache__` component and a `.pyc` suffix
are still skipped, and a benign ancestor such as `.pycharm` is not — the latter
is the assertion that would have caught this.

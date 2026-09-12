---
title: mirror-drift-guard-reports-byte-for-byte-match-while-comparing-nothing
summary: "scripts/sync_plugin_assets.py's __pycache__/.pyc exclusion substring-matches the ABSOLUTE path instead of the path's parts and suffix, so on any checkout whose directory name contains one of those fragments every source and destination item is skipped. --check then prints \"OK — byte-for-byte\" having compared nothing, and the pre-commit auto-sync stages nothing. The three sibling implementations of the identical exclusion all scope it correctly to .parts/.suffix."
status: done
stage: null
contribution: medium
created: "2026-09-10T04:51:50Z"
closed_at: "2026-09-12T04:33:16Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — `--check` reports drift for a corrupted mirror and a deleted hook on a checkout under a `.pyc`-containing path
  - [x] TDD: a regression test pins `_skip` itself — the exclusion matches `__pycache__` components and `.pyc` suffixes, and does NOT match a benign ancestor directory named e.g. `.pycharm`
  - [x] MECHANICAL: `_skip` scopes its test to `path.parts` / `path.suffix`, matching the three sibling sites (`scripts/port_skills_to_openclaw.py:240`, `goc/install.py:938`, `goc/install.py:1194`)
  - [x] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` pass
worker: {who: "claude[bot]", where: main}
---

# The mirror drift guard reports a byte-for-byte match while comparing nothing

Fixed. `_skip` now scopes its exclusion to the path's own components and
suffix, so the sync and its `--check` do real work on every checkout path.

## Location

`scripts/sync_plugin_assets.py` — the exclusion predicate, as it stood before
the fix (then at `:221` and `:235-237`):

```python
_SKIP_FRAGMENTS = ("__pycache__", ".pyc")


def _skip(path: Path) -> bool:
    s = str(path)
    return any(frag in s for frag in _SKIP_FRAGMENTS)
```

`_skip` is called at ten sites in the walk, on absolute source and destination
paths.

## What was broken

The exclusion is meant to skip compiled-Python artifacts: `__pycache__`
directories and `.pyc` files. It tested the fragments against `str(path)` of the
**absolute** path, so it also matched any ancestor directory whose name happened
to contain one — `.pycharm/`, `~/dev/.pyc-cache/`, a branch checkout named
`fix-pyc-handling`, and so on.

When that happened, every item the walk offered was "skipped". The sync copied
nothing and the guard compared nothing — and reported the empty comparison as
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
mirrored hook deleted.

Before the fix — `--check` exits 0 both before and after the corruption, and the
plain sync run is a total no-op:

```
baseline   : exit=0 :: OK — plugin payloads + dogfood self-host copies match goc/ and goc/templates/ byte-for-byte.
after drift: exit=0 :: OK — plugin payloads + dogfood self-host copies match goc/ and goc/templates/ byte-for-byte.
sync run   : (no output — total no-op)
after sync : content still drifted=True, hook still missing=True

[FAIL] --check reported success with a corrupted mirror and a deleted hook: the guard compared nothing.
```

After the fix — `--check` fails on the injected drift, and the sync repairs both:

```
baseline   : exit=0 :: OK — plugin payloads + dogfood self-host copies match goc/ and goc/templates/ byte-for-byte.
after drift: exit=1 :: Fix: run `python scripts/sync_plugin_assets.py` and commit the result.
sync run   : exit=1 :: (no stdout — git add fails outside a repo)
after sync : content still drifted=False, hook still missing=False

[OK] the guard detects drift under a checkout path containing '.pyc'.
```

The `sync run` line reports the script's exit and stdout separately because the
extracted fixture is not a git repo: the script writes the repaired files, then
its closing `git add` of those paths fails. Empty stdout there means "nothing
staged", not "nothing done" — the `after sync` line is what distinguishes a
no-op from a repair, and the fixture's reported line was reworded to say so.

## Why it matters

AGENTS.md makes this script the load-bearing guard for four mirror trees:

> CI runs `python scripts/sync_plugin_assets.py --check` and fails the build on
> any drift, so editing only `.claude/skills/...` or `.codex/skills/...` is now
> CI-detectable (it gets overwritten by the next pre-commit pass).

Both halves of that guarantee failed together on an affected checkout: the
pre-commit hook stopped regenerating the mirrors, so a template edit shipped
without its mirrors, and `--check` stayed green so nothing surfaced it. The
failure mode was worse than a missing check, because the output actively
asserted the payloads match.

The trigger was a property of the *checkout path*, not the repo, which bounds
who was affected — GitHub Actions runners use `/home/runner/work/...`, so CI was
never hit — but it also meant the same commit passed for one contributor and
silently no-opped for another, with no signal distinguishing the two.

This is a sibling of
[sync-mechanisms-reimplement-orphan-pruning-and-drift-detection-and-keep-drifting](../sync-mechanisms-reimplement-orphan-pruning-and-drift-detection-and-keep-drifting/),
which catalogues the same script's duplicated walk logic. That umbrella is
scoped to orphan pruning and drift detection and does not cite the exclusion
predicate, so this closure leaves it untouched; the failure mode here was a
whole-guard no-op rather than a retained orphan, and the fix was a one-line
scoping change that needed no decision.

## Fix — landed

`scripts/sync_plugin_assets.py` — the test is scoped to the path's own
components and suffix, as the three sibling sites already do, and
`_SKIP_FRAGMENTS` is gone with its last reader:

```python
def _skip(path: Path) -> bool:
    """True for compiled-Python artifacts: `__pycache__` dirs and `.pyc` files.
    ...
    """
    return "__pycache__" in path.parts or path.suffix == ".pyc"
```

`tests/test_sync_skip_predicate_scope.py` pins both directions: a `__pycache__`
component and a `.pyc` suffix are still skipped; benign ancestors
(`.pycharm/`, `.pyc-cache/`, `fix-pyc-handling/`) and near-misses
(`__pycache__old/`, `engine.pyc.bak`) are not — the latter is the assertion that
would have caught this. Two further tests exercise `_sync_dir` and
`_check_changes` on a tree rooted under `.pycharm/checkout`, so the whole-guard
no-op is covered end to end and not just at the predicate. Against the old
substring predicate the file fails 6 assertions; against the fix all 4 tests
pass.

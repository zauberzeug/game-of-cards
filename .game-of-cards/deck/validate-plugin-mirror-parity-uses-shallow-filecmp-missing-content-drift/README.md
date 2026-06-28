---
title: validate-plugin-mirror-parity-uses-shallow-filecmp-missing-content-drift
summary: "`validate_plugin_mirror_parity` in `goc/engine.py` builds its dir comparison via `filecmp.dircmp(src, dst)`, which uses Python's default shallow comparison (size + mtime + mode). A hand-edit to a mirror file that preserves length and mtime is reported as identical, so `goc validate` returns green while `scripts/sync_plugin_assets.py --check` (the CI tripwire, which uses `shallow=False`) still flags it. Fix is to switch the engine's directory walk to deep content comparison so the two tripwires agree."
status: done
stage: null
contribution: high
created: "2026-05-30T14:00:56Z"
closed_at: "2026-05-30T14:04:45Z"
human_gate: none
advances:
  - extend-skill-parity-tripwire-to-claude-plugin-mirrors
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py demonstrates the stdlib gap (`filecmp.dircmp` reports same-length/same-mtime/content-different files as identical while `filecmp.cmp(shallow=False)` rejects them) that the engine's directory walk was exposing
  - [x] TDD: `tests/test_plugin_mirror_parity.py::test_same_length_same_mtime_drift_is_detected` covers the same-length / same-mtime / different-content case and asserts `validate_plugin_mirror_parity` reports drift
  - [x] MECHANICAL: `goc/engine.py:validate_plugin_mirror_parity` now constructs its `dircmp` via `_DeepDircmp`, whose `phase3` calls `filecmp.cmpfiles(..., shallow=False)` — the verdict matches `scripts/sync_plugin_assets.py --check`
  - [x] PROCESS: `uv run python -m unittest discover -s tests` is green (299 tests)
  - [x] PROCESS: `uv run goc validate` is green
worker: {who: "claude[bot]", where: main}
---

# validate-plugin-mirror-parity-uses-shallow-filecmp-missing-content-drift

## Location

`goc/engine.py:1185` — the dir-mirror branch of `validate_plugin_mirror_parity`:

```python
diffs = _walk(filecmp.dircmp(src, dst), src_rel, dst_rel, exclude=exclude)
```

`_walk` (`goc/engine.py:1019-1047`) reads `cmp.diff_files`, which
`filecmp.dircmp` populates via `filecmp.cmpfiles(..., shallow=True)` —
Python's default. Shallow comparison declares two files identical when
`os.stat()` returns the same size, mtime, and mode for both; the file
contents are never read.

## What's broken

The byte-mirror contract that the plugin distribution rests on
(documented in AGENTS.md: "Plugin assets are auto-synced — edit only
the template") is enforced by two tripwires that disagree on what
"same" means:

- **`scripts/sync_plugin_assets.py --check`** — CI's enforcement step.
  Compares with `filecmp.cmp(src, dst, shallow=False)` at four call
  sites (lines 275, 322, 477, 503). Reads file contents; correct.

- **`goc/engine.py:validate_plugin_mirror_parity`** — pre-commit's
  enforcement step, fired via `goc validate`. Uses
  `filecmp.dircmp(src, dst)` for directory pairs (line 1185). Shallow
  comparison by default; misses content drift when size and mtime
  happen to match.

The same function's *file*-level branch (line 1193) already uses
`shallow=False` — so within one function, two adjacent code paths
disagree on the comparison semantic.

Note the contradiction with the closed parent card
[extend-skill-parity-tripwire-to-claude-plugin-mirrors](../extend-skill-parity-tripwire-to-claude-plugin-mirrors/),
whose DoD line "`goc validate` … reproduces the CI byte-for-byte parity
check across all four mirror pairs" was marked done but is not actually
satisfied for the directory pairs.

## Empirical evidence

`uv run python .game-of-cards/deck/validate-plugin-mirror-parity-uses-shallow-filecmp-missing-content-drift/reproduce.py`:

```
filecmp.dircmp (used by goc/engine.py:1185):
  diff_files: []
  same_files: ['file.txt']
filecmp.cmp(shallow=False) (used by scripts/sync_plugin_assets.py):
  False
verdict: dircmp says identical, deep cmp says different — engine
         tripwire silently misses content drift in the plugin mirrors.
```

## Why it matters

The plugin payload (`claude-plugin/`, `codex-plugin/`,
`openclaw-plugin/`) is what every consumer of the plugin distribution
loads. AGENTS.md is explicit that those mirrors must be byte-for-byte
copies of the source-of-truth — symlinks and stale copies silently
break consumer installs. The local `goc validate` tripwire exists so
that drift is caught before push (the closed parent card explains: "the
whole point of having a tripwire — extending it to the plugin mirrors
closes the loop"). Today, the tripwire returns false negatives:

**Reachability path.** Any contributor who hand-edits a file under
`claude-plugin/goc/`, `codex-plugin/goc/`, or `openclaw-plugin/goc/`
with a same-length change (renaming a local variable, fixing a typo,
swapping two equivalent lines) bypasses the engine's pre-commit check.
A `git checkout` resets every working-tree file's mtime to the same
checkout-time stamp, so the size+mtime tuple of source and mirror
trivially match on a fresh CI clone too. Only the CI step that shells
out to `sync_plugin_assets.py --check` catches the drift — which is
exactly the failure mode the parent card was filed to prevent.

`pre-commit run --all-files` runs `uv run goc validate`, so the local
fast-feedback path is the affected one; contributors discover the drift
minutes later in red CI.

## Fix

`filecmp.dircmp` is parametric over comparison policy via subclassing:
override `phase3` to call `filecmp.cmpfiles(..., shallow=False)`, plus
update the class-level `methodmap` so the `same_files` / `diff_files` /
`funny_files` lazy attributes invoke the deep variant. Subdirectories
are visited via `self.__class__` in `phase4`, so a single subclass
propagates through the whole walk.

Concrete change in `goc/engine.py` (inside or hoisted just above
`validate_plugin_mirror_parity`):

```python
class _DeepDircmp(filecmp.dircmp):
    """Like `filecmp.dircmp` but compares file contents (`shallow=False`).

    `filecmp.dircmp` defaults to a shallow stat-only comparison: two
    files are reported as identical when their size, mtime, and mode
    match. That is wrong for the plugin-mirror tripwire — a hand-edit
    that preserves length and mtime silently slips past. This subclass
    overrides `phase3` (and re-points `methodmap` so the lazy
    `same_files`/`diff_files`/`funny_files` attributes use it) to call
    `filecmp.cmpfiles(..., shallow=False)`. Subdirs propagate via
    `self.__class__` in `phase4`.
    """

    def phase3(self):
        same, diff, funny = filecmp.cmpfiles(
            self.left, self.right, self.common_files, shallow=False
        )
        self.same_files = same
        self.diff_files = diff
        self.funny_files = funny

    methodmap = dict(
        filecmp.dircmp.methodmap,
        same_files=phase3,
        diff_files=phase3,
        funny_files=phase3,
    )
```

Then replace `filecmp.dircmp(src, dst)` at line 1185 with
`_DeepDircmp(src, dst)`. The two enforcement paths agree afterward.

## Cross-references

- [extend-skill-parity-tripwire-to-claude-plugin-mirrors](../extend-skill-parity-tripwire-to-claude-plugin-mirrors/)
  — the parent card whose DoD this restores.
- `scripts/sync_plugin_assets.py:275,322,477,503` — the four CI
  comparison sites that already use the correct `shallow=False`.

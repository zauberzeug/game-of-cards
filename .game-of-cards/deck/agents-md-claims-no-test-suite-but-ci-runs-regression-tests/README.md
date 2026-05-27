---
title: agents-md-claims-no-test-suite-but-ci-runs-regression-tests
summary: "AGENTS.md's `Common commands` section states `No pytest suite exists yet` and describes CI as only a build + console-script + `goc validate` smoke matrix. Both claims are stale: `tests/` holds 17 files / 165 passing tests, and `ci.yml` runs a `Run regression tests` step (`unittest discover -s tests`) on every push. An agent reading AGENTS.md will wrongly believe there is no test suite to run or extend when fixing a bug."
status: open
stage: null
contribution: medium
created: "2026-05-27T11:34:40Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [documentation]
definition_of_done: |
  - [ ] MECHANICAL: AGENTS.md no longer states "No pytest suite exists yet"; it describes the `tests/` regression suite and how CI runs it.
  - [ ] MECHANICAL: the `## Common commands` block lists a command to run the regression suite locally.
  - [ ] MECHANICAL: the CI description in AGENTS.md names the regression-test step alongside build/console-script/`goc validate`.
  - [ ] PROCESS: `goc validate` clean and the regression suite still passes after the edit.
---

# AGENTS.md claims no test suite exists, but CI runs a full regression suite

## Location

`AGENTS.md:33-35` (the `## Common commands` section, human-authored —
above the `<!-- BEGIN GOC -->` marker block).

## What's broken

AGENTS.md tells agents:

> No pytest suite exists yet. `.github/workflows/ci.yml` is a
> build + console-script + `goc validate` smoke matrix on Python
> 3.10-3.13; the validation step is what gates card-frontmatter drift.

Both halves of that claim are stale:

1. **A test suite exists.** `tests/` holds 17 test modules
   (`test_yaml_lite.py`, `test_board.py`, `test_install.py`,
   `test_validate_blocker_coherence.py`, `test_version_surfaces.py`,
   `test_plugin_mirror_parity.py`, etc.). It is written with the stdlib
   `unittest` framework but runs cleanly under pytest — 165 tests pass.
2. **CI runs that suite on every push.** `.github/workflows/ci.yml:50-51`:

   ```yaml
   - name: Run regression tests
     run: uv run python -m unittest discover -s tests
   ```

   So CI is *not* merely a "build + console-script + `goc validate`
   smoke matrix" — it is also a regression gate. The `goc validate`
   step gates card-frontmatter drift, but it is no longer the only
   correctness gate.

The `## Common commands` block also omits any command for running the
suite locally, even though it lists `uv run goc validate`, `uv build`,
and the sync-check. An agent following the documented commands has no
listed way to run the tests.

## Why it matters

AGENTS.md is the cold-read briefing for every agent that touches this
repo. An agent that believes "no pytest suite exists yet" will not run
the tests before/after a change and may not think to extend them when
fixing a bug — even though CI will fail the PR on a regression. The
guidance actively misdirects the audience it exists to serve.

This is doc drift: the test suite was added (see `git log -- tests/`)
without updating the prose that says it does not exist.

## Fix

Rewrite `AGENTS.md:33-35` to reflect reality. Concretely:

- Drop "No pytest suite exists yet."
- State that `tests/` is a `unittest`-based regression suite run in CI
  via `uv run python -m unittest discover -s tests`, and that CI is a
  build + console-script + regression-test + `goc validate` matrix on
  Python 3.10-3.13.
- Add the local test command to the `## Common commands` code block,
  e.g. `uv run python -m unittest discover -s tests   # regression suite`.

Verify the test-file count and pass total quoted in this card against
the tree at fix time (they may grow), then update the prose to match
whatever is current rather than hard-coding today's numbers.

MECHANICAL doc edit; no code change. `goc validate` and the existing
suite must stay green after the edit (the edit is to AGENTS.md, which
neither gates).

## DoD

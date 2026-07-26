---
title: vendored-engine-reports-co-installed-distribution-version-not-its-own
summary: "goc/__init__.py sets its __version__ literal, then unconditionally overwrites it with importlib.metadata.version(\"game-of-cards\") — which resolves the distribution record from the host interpreter's site-packages, not the package actually imported. An engine loaded via PYTHONPATH (all three plugin bin/goc wrappers) therefore reports whatever version a coexisting pip/pipx install is, corrupting .goc-version stamps, the AGENTS.md marker, and the upgrade 'already at' short-circuit."
status: open
stage: null
contribution: medium
created: "2026-07-24T01:09:58Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero and its verdict branch flips from `DEFECT REPRODUCED` to `DEFECT FIXED` — the repo engine keeps its `0.0.27` literal even with a foreign `game_of_cards-9.9.9.dist-info` on the import path.
  - [ ] TDD: a regression test in `tests/` covers the chosen guard (fake dist-info on sys.path; assert the imported engine reports its own literal), and the full suite (`uv run python -m unittest discover -s tests`) passes.
  - [ ] MECHANICAL: the chosen fix (see `## Decision required`) lands in `goc/__init__.py` and propagates to the three plugin mirrors via `scripts/sync_plugin_assets.py`; `python scripts/sync_plugin_assets.py --check` is green.
  - [ ] MECHANICAL: the release-workflow interaction is handled — either the commit landing this fix is verified not to break the HEAD-only tripwire at the next dispatch, or the tripwire guidance is updated alongside (cross-check with [release-tripwire-only-inspects-the-head-commit-for-version-literal-edits](../release-tripwire-only-inspects-the-head-commit-for-version-literal-edits/)).
  - [ ] PROCESS: `uv run goc validate` passes.
---

# Vendored engine reports a co-installed distribution's version, not its own

## Summary

`goc/__init__.py` declares a `__version__` literal (kept release-accurate by
`scripts/release_rewrite_versions.py`), then unconditionally replaces it with
`importlib.metadata.version("game-of-cards")`. That lookup resolves the
*distribution metadata* visible to the interpreter — normally site-packages —
not the package that was actually imported. When the engine is loaded from a
path install (the plugin wrappers set `PYTHONPATH` to the plugin root), any
coexisting pip/pipx install of `game-of-cards` wins the version report, and
`PYTHONPATH` order cannot protect the vendored engine because the plugin
payload ships no `.dist-info`.

## Location

- `goc/__init__.py:7-17` — the unconditional overwrite:

  ```python
  __version__ = "0.0.27"

  try:
      from importlib.metadata import PackageNotFoundError, version as _pkg_version
  except ImportError:
      pass
  else:
      try:
          __version__ = _pkg_version("game-of-cards")
      except PackageNotFoundError:
          pass
  ```

- `claude-plugin/bin/goc:25` — the vendored-engine launch shape that makes
  the skew reachable:
  `exec env PYTHONPATH="${PLUGIN_ROOT}:${PYTHONPATH:-}" "$PYTHON" -m goc.cli "$@"`
  (the codex and openclaw wrappers use the same pattern).

## What's broken

The literal is authoritative for the vendored engine — AGENTS.md's release
section says the release workflow rewrites "`goc/__init__.py`'s `__version__`
literal" precisely "so consumers reading the git tree directly — plugin
managers read the checked-in payloads — see the correct version." But the
metadata fallback assumes the only failure mode is *no* distribution
(`PackageNotFoundError`); it has no guard for a *different* installation's
metadata describing code that was never imported.

Downstream consumers of the lie:

- `goc/install.py:1565` and `:1825` — `.goc-version` stamped with the wrong
  version on install/upgrade.
- `goc/install.py:33` — `GOC_BEGIN = f"<!-- BEGIN GOC v{__version__} -->"`,
  so the AGENTS.md marker block advertises the wrong version.
- `goc/install.py:1755`/`:1764` — the upgrade short-circuit
  `existing == __version__` → `"already at goc {__version__} — nothing to
  do."` Worst case: a repo stamped by a pip-installed 0.0.20 CLI runs
  `goc upgrade` through the 0.0.27 plugin wrapper; `__version__` resolves to
  0.0.20, the equality short-circuit fires, and the newer templates never
  land — 0.0.27 code prints "already at goc 0.0.20 — nothing to do."

## Empirical evidence

`uv run python .game-of-cards/deck/vendored-engine-reports-co-installed-distribution-version-not-its-own/reproduce.py`
(offline — fabricates a metadata-only `game_of_cards-9.9.9.dist-info` on the
import path, no code behind it):

```
engine imported from : /home/runner/work/game-of-cards/game-of-cards/goc/__init__.py
__version__ literal  : 0.0.27
reported __version__ : 9.9.9
DEFECT REPRODUCED: the repo's own engine reports the co-installed distribution's metadata version, not its own literal
```

A hunter agent additionally confirmed the realistic direction with a real
venv: with `game-of-cards==0.0.26` pip-installed,
`PYTHONPATH=<repo> venv/bin/python -c "import goc; print(goc.__file__,
goc.__version__)"` printed the repo's `goc/__init__.py` path (literal 0.0.27)
but version `0.0.26`.

## Why it matters

The docs themselves recommend `pipx install game-of-cards` as the fallback
alongside the plugin, so plugin + pip dual installs are an expected consumer
configuration, and the plugin payload routinely lags or leads the pip install
by a release. Every dual-install host runs the vendored engine with a
version identity taken from the *other* install: `goc --version` lies,
`.goc-version` sentinels record the wrong provenance, and `goc upgrade` can
permanently short-circuit (see above). Reachability path: plugin `bin/goc`
wrapper → `PYTHONPATH` import of the vendored package → `importlib.metadata`
resolving the co-installed `.dist-info` from site-packages.

This composes badly with
[goc-upgrade-silently-downgrades-newer-install-without-guard-or-warning](../goc-upgrade-silently-downgrades-newer-install-without-guard-or-warning/):
the version skew this card creates is exactly what makes the direction of a
silent downgrade invisible. It is mechanism-distinct from
[npm-tarball-ships-vendored-engine-reporting-previous-release-version](../npm-tarball-ships-vendored-engine-reporting-previous-release-version/),
which is about a stale *literal* baked into the npm artifact; this card is
about a correct literal being overridden at import time by foreign metadata.

## Decision required

All three options kill the hijack shown by `reproduce.py`; they differ in
what the metadata fallback still buys and in developer-mode behavior:

1. **Strict identity check.** Accept the metadata version only when the
   `game-of-cards` distribution actually provides the imported module:
   resolve `distribution("game-of-cards").locate_file("goc/__init__.py")`
   and compare against `__file__`. Wheel/sdist installs keep today's
   behavior (metadata wins, including dev versions from git installs);
   vendored/PYTHONPATH engines keep their literal. Side effect: PEP 660
   editable installs (`uv pip install -e .`, what CI and dev envs use) fail
   the path check and start reporting the literal instead of the hatch-vcs
   dev version.
2. **Identity check plus editable-aware exemption.** As (1), but also accept
   the metadata when the distribution's PEP 610 `direct_url.json` marks an
   editable install whose URL contains `__file__`. Preserves dev-version
   reporting at the cost of noticeably more logic in `__init__.py`.
3. **Drop the metadata fallback entirely.** The release workflow already
   rewrites the literal at every release, so the literal is authoritative
   for every published channel; only pip-installs from untagged git lose
   their `.devN` version report. Simplest and most predictable.

Whichever option lands, note the fix edits `goc/__init__.py` — one of the
six files the release tripwire tracks. The tripwire only inspects HEAD at
dispatch time, so the practical risk is a release dispatched while this fix
is HEAD; coordinate with
[release-tripwire-only-inspects-the-head-commit-for-version-literal-edits](../release-tripwire-only-inspects-the-head-commit-for-version-literal-edits/).

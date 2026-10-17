---
title: plugin-payload-still-declares-click-and-pyyaml-dependencies-the-engine-dropped
summary: "FIXED: claude-plugin/ shipped the pyproject.toml and uv.lock that existed only so the old bin/goc wrapper could run uv run --project against them; for five months after the wrapper stopped using uv and the engine dropped both packages, they declared click and pyyaml (and locked colorama) as the plugin engine's dependencies, against the pure-stdlib contract the plugin README states. Both files are deleted, and tests/test_plugin_payload_dependency_manifests.py fails if any plugin payload tracks a Python manifest or lockfile whose runtime declarations name a package its bundled goc/ does not import."
status: done
stage: null
contribution: low
created: "2026-10-16T04:54:13Z"
closed_at: "2026-10-17T04:50:57Z"
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — the plugin payload declares and locks no package its bundled engine does not import.
  - [x] MECHANICAL: `claude-plugin/pyproject.toml` and `claude-plugin/uv.lock` are removed (nothing in the payload or the release flow reads them), and the `scripts/sync_plugin_assets.py` docstring stops listing `claude-plugin/pyproject.toml` as a hand-maintained plugin file.
  - [x] TDD: a regression test fails if any plugin payload (`claude-plugin/`, `codex-plugin/`, `openclaw-plugin/`) tracks a Python dependency manifest or lockfile that declares a package the bundled `goc/` does not import. Fed the pre-fix `pyproject.toml` verbatim, the test fails, so it is proven able to fire.
  - [x] PROCESS: `python scripts/sync_plugin_assets.py --check` green, `uv run goc validate` clean, full `unittest` suite green; the meta card's instance list gains this card's row.
worker: {who: "claude[bot]", where: main}
---

# The plugin payload still declares click and pyyaml dependencies the engine dropped

## Location

- `claude-plugin/pyproject.toml` (deleted) — a `goc-plugin-engine 0.0.0`
  project declaring `dependencies = ["click>=8.1", "pyyaml>=6.0"]`.
- `claude-plugin/uv.lock` (deleted) — the matching lockfile, pinning
  `click 8.3.3`, `colorama 0.4.6` and `pyyaml 6.0.3`.
- `scripts/sync_plugin_assets.py:60-63` — the `_build_sync_pairs` docstring,
  which listed `claude-plugin/pyproject.toml` among the hand-maintained
  plugin files.
- `.claude-plugin/marketplace.json:14` — `"source": "./claude-plugin"`.
  The marketplace installs this whole subtree, so both files shipped.

## What was broken

Both files belonged to the plugin's first runtime shape. Commit `26bfce00`
(2026-05-08, `bundle-goc-engine-inside-plugin-payload`) made `bin/goc` run
`uv run --project ${PLUGIN_ROOT}`. That card recorded why the manifest
existed: "The plugin's `claude-plugin/pyproject.toml` declares the same two
runtime deps (`click>=8.1`, `pyyaml>=6.0`) that the package needs. uv builds
an isolated venv … on first call."

A day later the `drop-third-party-runtime-dependencies-from-goc` epic
removed both packages from the engine. Its last child, `plugin-wrapper-drops-uv`
(commit `8d64a3fb`), switched the wrapper to `python3 -m goc.cli`. That
commit touched `bin/goc`, the plugin README and `CLAUDE.md`, but neither
file the old wrapper had consumed, so both kept asserting the old
dependency set:

```toml
# claude-plugin/pyproject.toml
[project]
name = "goc-plugin-engine"
version = "0.0.0"
...
dependencies = [
    "click>=8.1",
    "pyyaml>=6.0",
]
```

Every other source said the opposite:

- root `pyproject.toml`: `dependencies = []`;
- `claude-plugin/README.md:47-49`: "The plugin is self-contained — no
  `pip install`, `pipx install`, or `uv` required. The bundled engine is
  pure-stdlib Python and runs via the `python3` already on your PATH.";
- `claude-plugin/bin/goc`: "No venv, no uv, no first-call latency."

Nothing read the manifest anymore. Claude Code reads a plugin through
`.claude-plugin/plugin.json`, the wrapper never calls `uv`, and the
release workflow rewrites five plugin manifests but not this one, which
is why its `version` stayed `0.0.0` from creation to deletion.

## Empirical evidence

`uv run python .game-of-cards/deck/plugin-payload-still-declares-click-and-pyyaml-dependencies-the-engine-dropped/reproduce.py`
before the fix, exit status 1:

```text
claude-plugin/pyproject.toml dependencies : ['click', 'pyyaml']
claude-plugin/uv.lock packages            : ['click', 'colorama', 'pyyaml']
root pyproject.toml dependencies          : [] (pure stdlib)
third-party imports in claude-plugin/goc/ : none
bin/goc runs uv                           : False
payload files reading the manifest        : none

declared or locked but never imported     : ['click', 'colorama', 'pyyaml']
```

After the fix, exit status 0:

```text
claude-plugin/pyproject.toml dependencies : none (file absent or empty)
claude-plugin/uv.lock packages            : none (file absent)
root pyproject.toml dependencies          : [] (pure stdlib)
third-party imports in claude-plugin/goc/ : none
bin/goc runs uv                           : False
payload files reading the manifest        : none

declared or locked but never imported     : none
```

On the pre-fix tree the new guard's live check reported four lines:
`click` and `pyyaml` in each of `claude-plugin/pyproject.toml` and
`claude-plugin/uv.lock`. It does not report `colorama`, which `reproduce.py`
counts: that is click's transitive pin, not a declaration (see "What
changed").

## Why it matters

Low stakes, but the files were wrong, and they shipped. Every Claude Code
marketplace install copied a manifest and lockfile into the user's plugin
cache. Both said the plugin engine depends on third-party packages, and
the plugin's own README says it depends on none. Anyone who trusted the
manifest was misled: a dependency or license scanner pointed at the plugin,
or a contributor who ran `uv sync` in `claude-plugin/` and got a venv
nothing uses. And `sync_plugin_assets.py` documented the manifest as a
file someone maintains by hand.

It is also the third shipped surface to carry the same stale fact, that
goc needs click. [agents-md-architecture-section-cites-removed-click-and-omits-verbs](../agents-md-architecture-section-cites-removed-click-and-omits-verbs/)
fixed it in `AGENTS.md` and `goc/cli.py`.
[openclaw-verb-mirror-comment-names-click-in-an-argparse-cli](../openclaw-verb-mirror-comment-names-click-in-an-argparse-cli/)
fixed it in a TypeScript comment two months later. This instance is a
package manifest, a machine-readable surface that a prose guard would
not scan. That supports
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/)'s
point that a guard keyed to the claim reaches surfaces a guard keyed to
files misses.

## What changed

- `claude-plugin/pyproject.toml` and `claude-plugin/uv.lock` are deleted.
  This follows from the recorded decision on
  `drop-third-party-runtime-dependencies-from-goc`: "plugin wrapper drops
  uv outright (python3-only, no fallback)". Nothing in the payload, the
  sync script, CI or the release workflow read either file.
- The `_build_sync_pairs` docstring in `scripts/sync_plugin_assets.py`
  lists `claude-plugin/.claude-plugin/plugin.json` where the manifest
  was, the Claude counterpart of the Codex manifest the same sentence
  names.
- `tests/test_plugin_payload_dependency_manifests.py` (new) derives both
  sides of the claim instead of restating either. A payload is any tracked
  top-level directory that bundles the engine as `<dir>/goc/`, so a fourth
  payload is covered without an edit. The import set comes from an `ast`
  walk of that bundled copy, minus stdlib and `goc` itself; an installed
  module resolves to its distribution through package metadata, so `yaml`
  counts as PyYAML. The declared set comes from every `pyproject.toml`,
  `uv.lock` and `requirements*.txt` the payload tracks.
- Only runtime declarations count: `[project]` dependencies and extras, the
  uv project entry's own dependencies, and requirement lines. A build
  backend, a dev group or a lockfile's transitive pins say nothing about
  what the engine imports, and counting them would turn a legitimate
  future manifest red. Any other Python manifest or lockfile (`setup.py`,
  `setup.cfg`, `Pipfile`, `Pipfile.lock`, `poetry.lock`, `pdm.lock`,
  `pylock*.toml`) fails outright. Nothing builds or installs a payload,
  and a format the guard cannot read should not pass unread.
- `PreFixManifestFiresTest` feeds the pre-fix `pyproject.toml` (verbatim)
  and `uv.lock` (hashes elided) through the same check against the real
  bundled engine and gets click and pyyaml for each. `ManifestFormatTest`
  shows each reader firing on a package the engine does not import and
  staying quiet once the engine imports it. Reading TOML needs `tomllib`,
  so on CI's Python 3.10 leg the fixture tests skip, and the live check
  skips only when a TOML manifest is present; the 3.11+ legs run all six.

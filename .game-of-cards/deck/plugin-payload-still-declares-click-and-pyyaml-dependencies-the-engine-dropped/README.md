---
title: plugin-payload-still-declares-click-and-pyyaml-dependencies-the-engine-dropped
summary: "claude-plugin/ still ships the pyproject.toml and uv.lock that existed only so the old bin/goc wrapper could run uv run --project against them; they declare click and pyyaml (and lock colorama) as the plugin engine's dependencies. The wrapper stopped using uv in May, the engine imports neither package, and the root package declares no dependencies, so every marketplace install carries a manifest and lockfile that contradict the pure-stdlib contract the plugin README states."
status: open
stage: null
contribution: low
created: "2026-10-16T04:54:13Z"
closed_at: null
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — the plugin payload declares and locks no package its bundled engine does not import.
  - [ ] MECHANICAL: `claude-plugin/pyproject.toml` and `claude-plugin/uv.lock` are removed (nothing in the payload or the release flow reads them), and the `scripts/sync_plugin_assets.py` docstring stops listing `claude-plugin/pyproject.toml` as a hand-maintained plugin file.
  - [ ] TDD: a regression test fails if any plugin payload (`claude-plugin/`, `codex-plugin/`, `openclaw-plugin/`) tracks a Python dependency manifest or lockfile that declares a package the bundled `goc/` does not import. Fed the pre-fix `pyproject.toml` verbatim, the test fails, so it is proven able to fire.
  - [ ] PROCESS: `python scripts/sync_plugin_assets.py --check` green, `uv run goc validate` clean, full `unittest` suite green; the meta card's instance list gains this card's row.
---

# The plugin payload still declares click and pyyaml dependencies the engine dropped

## Location

- `claude-plugin/pyproject.toml:1-22` — a `goc-plugin-engine 0.0.0`
  project declaring `dependencies = ["click>=8.1", "pyyaml>=6.0"]`.
- `claude-plugin/uv.lock` — the matching lockfile, pinning `click 8.3.3`,
  `colorama 0.4.6` and `pyyaml 6.0.3`.
- `scripts/sync_plugin_assets.py:60-63` — the docstring that still lists
  `claude-plugin/pyproject.toml` among the hand-maintained plugin files.
- `.claude-plugin/marketplace.json:14` — `"source": "./claude-plugin"`.
  The marketplace installs this whole subtree, both files included.

## What's broken

Both files belong to the plugin's first runtime shape. Commit `26bfce00`
(2026-05-08, `bundle-goc-engine-inside-plugin-payload`) made `bin/goc` run
`uv run --project ${PLUGIN_ROOT}`. That card recorded why the manifest
existed: "The plugin's `claude-plugin/pyproject.toml` declares the same two
runtime deps (`click>=8.1`, `pyyaml>=6.0`) that the package needs. uv builds
an isolated venv … on first call."

A day later the `drop-third-party-runtime-dependencies-from-goc` epic
removed both packages from the engine. Its last child, `plugin-wrapper-drops-uv`
(commit `8d64a3fb`), switched the wrapper to `python3 -m goc.cli`. That
commit touched `bin/goc`, the plugin README and `CLAUDE.md`, but neither
file the old wrapper had consumed, so both still assert the old
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

Every other source says the opposite:

- root `pyproject.toml`: `dependencies = []`;
- `claude-plugin/README.md:47-49`: "The plugin is self-contained — no
  `pip install`, `pipx install`, or `uv` required. The bundled engine is
  pure-stdlib Python and runs via the `python3` already on your PATH.";
- `claude-plugin/bin/goc`: "No venv, no uv, no first-call latency."

Nothing reads the manifest anymore. Claude Code reads a plugin through
`.claude-plugin/plugin.json`, the wrapper never calls `uv`, and the
release workflow rewrites five plugin manifests but not this one, which
is why its `version` has been `0.0.0` since it was created.

## Empirical evidence

`uv run python .game-of-cards/deck/plugin-payload-still-declares-click-and-pyyaml-dependencies-the-engine-dropped/reproduce.py`:

```text
claude-plugin/pyproject.toml dependencies : ['click', 'pyyaml']
claude-plugin/uv.lock packages            : ['click', 'colorama', 'pyyaml']
root pyproject.toml dependencies          : [] (pure stdlib)
third-party imports in claude-plugin/goc/ : none
bin/goc runs uv                           : False
payload files reading the manifest        : none

declared or locked but never imported     : ['click', 'colorama', 'pyyaml']
```

Exit status 1.

## Why it matters

Low stakes, but the files are wrong, and they ship. Every Claude Code
marketplace install copies a manifest and lockfile into the user's plugin
cache. Both say the plugin engine depends on three third-party packages,
and the plugin's own README says it depends on none. Anyone who trusts the
manifest is misled: a dependency or license scanner pointed at the plugin,
or a contributor who runs `uv sync` in `claude-plugin/` and gets a venv
nothing uses. And `sync_plugin_assets.py` still documents the manifest as
a file someone maintains by hand.

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

## Fix

Delete `claude-plugin/pyproject.toml` and `claude-plugin/uv.lock`. This
follows from the recorded decision on
`drop-third-party-runtime-dependencies-from-goc`: "plugin wrapper drops
uv outright (python3-only, no fallback)". With no uv fallback, nothing
needs the manifest, so the change is gate-free. Drop the
`claude-plugin/pyproject.toml` mention from the
`_build_sync_pairs` docstring in `scripts/sync_plugin_assets.py`. Add a
regression test that scans the three plugin payloads for Python
dependency manifests or lockfiles and fails on any declared package that
the bundled `goc/` does not import. That way, if a future runtime change
leaves a manifest behind, CI catches it.

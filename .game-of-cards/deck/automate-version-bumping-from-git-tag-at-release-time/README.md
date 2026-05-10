---
title: automate-version-bumping-from-git-tag-at-release-time
summary: "Make the git tag the single source of truth for the package version. Use hatch-vcs for the wheel and have the release workflow rewrite literals in goc/__init__.py and the four plugin manifests at build time, eliminating the six-file manual bump that drifted on 0.0.12."
status: active
stage: null
contribution: medium
created: 2026-05-10
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [infra]
definition_of_done: |
  - [ ] `pyproject.toml` declares `dynamic = ["version"]` and `[tool.hatch.version] source = "vcs"`; the literal `version = "X.Y.Z"` line is removed
  - [ ] `uv build` from a checkout at a tagged commit produces a wheel whose version matches the tag (verified locally for at least one dry-run tag)
  - [ ] `release.yml` build job parses `${GITHUB_REF#refs/tags/v}` and rewrites `__version__` in `goc/__init__.py` plus the `version` field in `openclaw-plugin/package.json`, `openclaw-plugin/package-lock.json` (both occurrences), `claude-plugin/.claude-plugin/plugin.json`, and `.claude-plugin/marketplace.json` before the publish steps run
  - [ ] `scripts/sync_plugin_assets.py` runs after the rewrite (or its byte-mirror still produces `claude-plugin/goc/__init__.py` and `openclaw-plugin/goc/__init__.py` with the new literal)
  - [ ] The existing `Verify tag matches pyproject + package.json versions` step in `release.yml` is removed (no longer meaningful — the workflow IS the version writer)
  - [ ] `dry_run` workflow_dispatch path still works end-to-end: pick an arbitrary version string, rewrite, build, smoke; assert artifacts carry that version without publishing
  - [ ] CI passes a tripwire that fails the build if `goc/__init__.py` or any of the 4 manifests is touched in the same commit as a tag push (humans should never edit these post-switch)
  - [ ] Documentation updated: `CLAUDE.md`'s release section reflects the new "tag is the version" flow; `release.yml` header comment rewritten to match
  - [ ] One real release published end-to-end (PyPI + npm + ClawHub) using only `git tag vX.Y.Z && git push --tags`, with no version edits in the commit that the tag points to
worker: {who: "claude[bot]", where: main}
---

# automate-version-bumping-from-git-tag-at-release-time

## Why

Today a version bump touches six files in three formats and is gated by
a tag-vs-pyproject-vs-package.json check that only covers two of them.
The 0.0.12 release shipped with `openclaw-plugin/package-lock.json`
still pinned at the previous version (commit `04182f0`, "fix: bump
package-lock.json to 0.0.12 (was missed)"); that drift was invisible
to the existing CI guard. The closed card
`investigate-fix-version-drift` (2026-05-04) decided the rule should
be "CI fails on any drift between live version surfaces", but the
broader check was never wired up — and the next release demonstrated
why a checker-on-six-files is fragile compared to deriving the version
from a single source.

## Approach (Option B — workflow rewrites literals)

Make the git tag the only place a human types a version. The release
workflow becomes the mechanical writer for every other surface.

### Surfaces and their new sources

| Surface | New source |
|---|---|
| Wheel version (`pyproject.toml`) | `hatch-vcs` reads it from the latest git tag at build time |
| `goc/__init__.py` (`__version__`) | release workflow rewrites the literal from the tag before sync runs |
| `openclaw-plugin/package.json` | release workflow rewrites the literal |
| `openclaw-plugin/package-lock.json` (both occurrences) | release workflow rewrites both |
| `claude-plugin/.claude-plugin/plugin.json` | release workflow rewrites the literal |
| `.claude-plugin/marketplace.json` | release workflow rewrites the literal |
| `claude-plugin/goc/__init__.py` | propagated by `sync_plugin_assets.py` (already automated) |
| `openclaw-plugin/goc/__init__.py` | propagated by `sync_plugin_assets.py` (already automated) |

### Why a workflow rewrite of `goc/__init__.py` instead of `importlib.metadata`

`importlib.metadata.version("game-of-cards")` only resolves when the
package is installed as a real distribution with a `*.dist-info/`
directory next to it on `sys.path`. The plugin payloads load `goc/`
as vendored source via `PYTHONPATH=$plugin_root` — there is no
`dist-info`, so the lookup raises `PackageNotFoundError` and the
plugin's `goc --version` would report nothing. A literal rewrite
sidesteps this asymmetry and keeps the source readable.

### Between-tag dev versions

`hatch-vcs` will report something like `0.0.12.dev3+g04182f0` from
checkouts on `main` between tags — its default `git describe` mode
is fine and informative. The literal in `goc/__init__.py` between
tags stays at the last released value (e.g. `0.0.12`); slightly
stale but never lying about being a dev build.

### Workflow shape

In `.github/workflows/release.yml`'s `build` job, after checkout and
before `uv build`:

1. `tag_version="${GITHUB_REF#refs/tags/v}"`
2. `python` one-liner or `sed -i` rewrites `goc/__init__.py`'s
   `__version__ = "..."` to the tag value
3. `jq` rewrites the four JSON manifests
4. Run `scripts/sync_plugin_assets.py` (so the bundled-engine copies
   pick up the new `__version__`)
5. `uv build` (hatch-vcs supplies the wheel version from the tag)
6. `npm install` in `openclaw-plugin/` to regenerate the lockfile at
   the new version (validates the rewrite was correct)

The `Verify tag matches…` step is removed — there is nothing to
verify against, because the workflow itself is the version writer.

### dry_run mode

`workflow_dispatch` with `dry_run: true` should still exercise the
rewrite path. Pick a synthetic version (e.g. `0.0.0-dryrun-${sha}`),
run the rewrite, build artifacts, run smoke, do not publish. This
catches breakage in the rewrite logic without needing a real tag.

### Tripwire

After this lands, humans must never edit version literals again. Add
a CI check (in `ci.yml` or `release.yml`'s build job) that fails if
any commit touching a tag also modifies `goc/__init__.py` or the
four manifests. This catches the failure mode where someone reverts
to the old habit and creates a "merge conflict" between hand-edited
and workflow-written values.

## Out of scope

- Switching to `_version.py` indirection (Option A from the design
  discussion). Considered and rejected: adds an extra file and an
  import indirection for cosmetic dev-version honesty in the plugin
  payloads. The literal rewrite is simpler.
- Automating the `git tag` step itself (e.g. via Release Drafter,
  semantic-release, or a "publish" workflow_dispatch button). The
  decision of *what version to cut* remains a human action; only
  the propagation of that decision is automated.

## Context

- `investigate-fix-version-drift` (closed 2026-05-04) — inventoried
  the version surfaces and decided "CI fails on drift". This card
  supersedes that decision with a stronger one: there is no drift to
  fail on, because there is one source of truth.
- 0.0.12 release sequence (`966f21d`, `04182f0`) — the immediate
  trigger; demonstrated that the tag-vs-pyproject-vs-package.json
  guard misses lockfile drift.
- `scripts/sync_plugin_assets.py` — existing byte-for-byte mirror of
  the engine into both plugin payloads. This card extends its
  effective coverage to `goc/__init__.py`'s `__version__` field
  without modifying the script (the script already mirrors the file
  byte-for-byte; the rewrite happens upstream of it).

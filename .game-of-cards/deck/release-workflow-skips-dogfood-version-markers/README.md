---
title: release-workflow-skips-dogfood-version-markers
summary: "The v0.0.17 release commit bumped the five manifest version literals but not the two dogfood self-host surfaces (`.game-of-cards/deck/.goc-version`, `AGENTS.md`'s `<!-- BEGIN GOC v… -->` marker). `tests/test_version_surfaces.py::test_self_hosted_generated_surfaces_match_package_version` correctly caught the drift on CI run 25674525151. Fix: extend `scripts/release_rewrite_versions.py` to also rewrite the dogfood surfaces, and add them to the workflow's commit-back `git add` list."
status: done
stage: null
contribution: medium
created: "2026-05-11T15:22:53Z"
closed_at: 2026-05-11T15:26:23Z
human_gate: none
advances: []
advanced_by:
  - release-workflow-leaves-plugin-manifest-version-stale-on-main
tags: [bug, infra]
definition_of_done: |
  - [x] Reproduce: confirm CI run 25674525151 failed with `AssertionError: '0.0.17' != '0.0.12'` from `test_self_hosted_generated_surfaces_match_package_version`, and `git show 6534039:.game-of-cards/deck/.goc-version` and `git show 6534039:AGENTS.md | grep 'BEGIN GOC'` still read `0.0.12`
  - [x] `scripts/release_rewrite_versions.py` rewrites `.game-of-cards/deck/.goc-version` (full file replace) and `AGENTS.md`'s `<!-- BEGIN GOC v… -->` marker, with `expected=1` assertions for both
  - [x] `.github/workflows/release.yml`'s "Commit rewrites back to main" step adds the two new files to the explicit `git add` list, and the workflow header comment documents the expanded surface set
  - [x] `CLAUDE.md` release section is extended to mention the two dogfood surfaces as additional rewrite targets
  - [x] Manual 0.0.17 fix is applied to `.game-of-cards/deck/.goc-version` and `AGENTS.md` on `main` so CI on subsequent push events stays green without waiting for the next release dispatch
  - [x] `uv run goc validate` + `python3 -m unittest tests.test_version_surfaces` both pass after the fix
worker: {who: rodja, where: main}
---

# release-workflow-skips-dogfood-version-markers

## What broke

The v0.0.17 release run (25674213757) succeeded end-to-end — wheel
built, all three registries published, bot committed the five
manifest version literals back to `main` as commit `6534039` with
subject `release: bump version literals to v0.0.17`. The Claude Code
plugin label now reads `0.0.17` correctly.

But the CI run that fired on the bot's release commit
([25674525151](https://github.com/zauberzeug/game-of-cards/actions/runs/25674525151))
failed with:

```
FAIL: test_self_hosted_generated_surfaces_match_package_version
AssertionError: '0.0.17' != '0.0.12'
```

The test reads `__version__` from `goc/__init__.py` (now `0.0.17`)
and asserts that the two dogfood self-host surfaces match:

- `.game-of-cards/deck/.goc-version` — still `0.0.12`
- `AGENTS.md`'s `<!-- BEGIN GOC v0.0.12 -->` marker — still `0.0.12`

These surfaces have always been written by `goc install` / `goc
upgrade`, never by the release workflow. Before the commit-back
landed, the on-main literal of `goc/__init__.py` was also `0.0.12`
(stuck at the first-released value), so the test passed by accident:
nothing in main was actually current, so everything matched at
`0.0.12`. The commit-back exposed the drift the test was built to
detect.

## Why the predecessor card missed it

`release-workflow-leaves-plugin-manifest-version-stale-on-main` was
scoped narrowly to the five publish-channel surfaces. The dogfood
self-host state was treated as orthogonal — historically updated by
`goc upgrade` rather than the release workflow. With the commit-back
step, the release workflow now IS the writer for the five manifest
literals on `main`, so the gap between "static literal in `goc/__init__.py`"
and "dogfood marker derived from `__version__`" becomes a CI failure
on every release.

## The fix

Mechanical extension of the existing pattern. Add the two surfaces
to `release_rewrite_versions.py`:

| Surface | Pattern |
|---|---|
| `.game-of-cards/deck/.goc-version` | full-file replace (`<version>\n`) |
| `AGENTS.md` | `<!-- BEGIN GOC v[^>]+ -->` → `<!-- BEGIN GOC v<version> -->` |

And add them to the workflow's commit-back `git add` list so the bot
release commit carries them along with the other seven.

A manual 0.0.17 fix to both files on `main` lets CI go green
immediately without waiting for v0.0.18 — same idempotent shape as
the original v0.0.17 release commit, just applied by hand.

## Out of scope

- Wholesale running `goc upgrade` in the release workflow. That
  would regenerate skill bodies, hook scripts, and the entire
  dogfood self-host tree — useful if those drift, but not the
  failure mode here. The narrow rewrite-script extension solves the
  reported regression without inviting scope creep.
- Adding the dogfood surfaces to the workflow's tripwire. The
  tripwire's purpose is "humans never bump version literals manually
  in the publish-channel files". `AGENTS.md` is human-edited for
  content (the section above the marker block is repo-specific);
  blocking human commits to it would be wrong. The CI test catches
  drift, which is the right tool.

---
title: release-workflow-leaves-plugin-manifest-version-stale-on-main
summary: "release.yml rewrites version literals in-workflow but never commits the rewrites back to main, so claude-plugin/.claude-plugin/plugin.json (and the four sibling manifests) stay frozen at the first-released value (0.0.12) on main forever. PyPI/npm/ClawHub all override their own version surface via publish artifacts or reusable-workflow input, but the Claude Code plugin manager clones the marketplace and reads plugin.json directly from the git tree — no override channel exists, so users on the Claude Code plugin see a stale version label after every release. Fix: have the build job commit the rewrites back to main and tag the rewrite commit; relax the tripwire to exempt bot release commits."
status: active
stage: null
contribution: medium
created: "2026-05-11T13:17:27Z"
closed_at: null
human_gate: none
advances: []
advanced_by:
  - automate-version-bumping-from-git-tag-at-release-time
tags: [bug, infra]
definition_of_done: |
  - [ ] Reproduce: at tag v0.0.16, confirm `git show v0.0.16:claude-plugin/.claude-plugin/plugin.json` still reads `"version": "0.0.12"` (the bug) and document the consumer symptom (Claude Code's `/plugin` view shows 0.0.12 while ClawHub/PyPI/npm correctly show 0.0.16)
  - [ ] release.yml's build job, after all consistency checks pass, commits the five rewritten files (`goc/__init__.py`, `openclaw-plugin/package.json`, `openclaw-plugin/package-lock.json`, `claude-plugin/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`) back to main with subject `release: bump version literals to vX.Y.Z`, then creates and pushes the tag on the new commit
  - [ ] The tripwire is updated to exempt commits whose author is `github-actions[bot]` AND whose subject starts with `release: bump version literals to v` — so the *next* release dispatch doesn't fail on the previous release's own commit
  - [ ] CLAUDE.md release section and `release.yml` header comment are updated to describe the commit-back step and clarify that main always reflects the *most recent shipped* version literal (lagging by at most one release dispatch, never by lifetime-of-repo)
  - [ ] A real release end-to-end (e.g. v0.0.17) verifies the fix: after the workflow finishes, `git show v0.0.17:claude-plugin/.claude-plugin/plugin.json` reads `"version": "0.0.17"` and Claude Code's `/plugin` view also shows 0.0.17 for a fresh install
  - [ ] The two parked predecessor cards (`automate-version-bumping-from-git-tag-at-release-time`, `release-yml-smoke-job-fails-on-tag-push-events`) are closed — both have their DoDs ticked, and their decision-gates have been resolved by subsequent cards
  - [ ] `uv run goc validate` passes
worker: {who: rodja, where: main}
---

# release-workflow-leaves-plugin-manifest-version-stale-on-main

## The visible bug

User report: the Claude Code plugin manager shows `game-of-cards 0.0.12`
while ClawHub and the GitHub tags both clearly show `v0.0.16`. The
plugin content the user actually has on disk is from `main`'s HEAD
(commit `6f9080e` at the time of report) — i.e. fully up to date —
but the *version label* the plugin manager displays comes straight
from `claude-plugin/.claude-plugin/plugin.json`'s `version` field, which
on main has read `"0.0.12"` since the first release with that file.

Verified at the v0.0.16 tag (2026-05-11):

```
$ git show v0.0.16:claude-plugin/.claude-plugin/plugin.json | jq .version
"0.0.12"
$ git show v0.0.16:goc/__init__.py | head -10
…
__version__ = "0.0.12"
```

The same is true at `v0.0.13`, `v0.0.14`, `v0.0.15`. Between
`v0.0.12..v0.0.16`, `git log` shows **zero commits** touching any of
the five tracked version files.

## Why the existing design didn't catch this

The predecessor card
`automate-version-bumping-from-git-tag-at-release-time` (closed-ish,
all DoDs ticked) made the workflow the single version writer. Its
design rewrites the literals **in the in-workflow checkout only**,
runs every consistency check on the rewritten tree, builds the wheel
with `SETUPTOOLS_SCM_PRETEND_VERSION`, and pushes the tag on `main`'s
HEAD as the last step. The tripwire at `release.yml:211` actively
*forbids* a commit that touches the listed files — humans must never
edit version literals.

For three of the four publish channels, that design works:

| Channel | Source for displayed version | Why it works today |
|---|---|---|
| PyPI | wheel built in-workflow | `SETUPTOOLS_SCM_PRETEND_VERSION` pins the wheel version regardless of the on-disk literal |
| npm | publish-npm job re-runs the rewrite, then `npm publish` | The publish job sees the rewritten files in its own checkout |
| ClawHub | `version:` input override to the reusable workflow | The reusable workflow's own checkout would read the stale literal; the override compensates |
| **Claude Code plugin** | **direct read of `plugin.json` from the git tree** | **No override mechanism exists** |

Claude Code's plugin manager clones the marketplace repo, copies the
`claude-plugin/` subtree byte-for-byte into the user's `~/.claude/`,
and renders the `version` field from the on-disk file directly. There
is no publish artifact, no input override, no build step on the plugin
side. Whatever the file says on `main` is what the user sees.

This is the architectural blind spot in the original design: it
assumed every consumer would read the version from a build artifact.
The Claude Code plugin loader violates that assumption — it reads the
git tree directly.

## The fix

Promote the rewrite from an in-job-only artifact to a real commit on
main. After all consistency checks pass (rewrite, sync, lockfile,
wheel-version assertion, artifact upload), the build job:

1. Stages the five tracked files
2. Commits with subject `release: bump version literals to vX.Y.Z`
   under the `github-actions[bot]` identity
3. Pushes the commit to main
4. Tags the new commit `vX.Y.Z`
5. Pushes the tag

The tag now points at a commit where the literals are correct. Main
also carries those literals, so any consumer reading the git tree
(Claude Code plugin loader, anyone browsing GitHub) sees the
correct value.

The tripwire — currently a flat "no version-literal edits in
HEAD" rule — gets one carve-out: it ignores commits authored by
`github-actions[bot]` whose subject starts with
`release: bump version literals to v`. This preserves the original
intent (humans never edit literals) while letting the workflow's own
release commit pass through on the next dispatch.

### Between-release accuracy

After this change, the on-main literal is the *previously shipped*
version. Between release dispatches, it lags by exactly one release.
That is a strict improvement over the current state, where the
literal lags by *every* release that has ever happened.

For development checkouts, `goc/__init__.py` still falls back to
`importlib.metadata.version("game-of-cards")` when installed as a
real distribution, so `goc --version` from a `pipx install` reports
the correct shipped version regardless of the source literal.

### Why not generate the file at install time

Claude Code's plugin manifest format is static JSON — there is no
template-evaluation step on the plugin manager side. The file must
be valid JSON on disk in the repo. Committing the rewrite is the
only mechanism that makes the version visible without changing how
Claude Code reads plugins.

### Why not rip the version field out of plugin.json

The field is required by Claude Code's plugin schema (it surfaces in
the `/plugin` view and is used for upgrade detection). Removing it
would mean users couldn't tell which release they have installed.

## Out of scope

- Switching `goc/__init__.py` to a `_version.py` indirection. Not
  needed — the literal-rewrite approach extends naturally to commit
  the literal back.
- Pre-commit-time enforcement of version-literal sync. The workflow
  already does this in-job; promoting it to a real commit is enough.
- Doing anything about the cosmetic two-line `__version__` literal in
  `claude-plugin/goc/__init__.py` and `openclaw-plugin/goc/__init__.py`
  beyond what `sync_plugin_assets.py` already mirrors. Those are
  byte-for-byte copies of `goc/__init__.py` and are handled by the
  existing sync step.

## Closing the parked predecessors

Both `automate-version-bumping-from-git-tag-at-release-time` and
`release-yml-smoke-job-fails-on-tag-push-events` have all DoD items
ticked. They are stuck at `human_gate: session` because each was
parked waiting on a downstream decision that has since been resolved
by a *different* card:

- `automate-version-bumping…` was parked on "the ClawHub publish
  source decision". That was answered by
  `find-single-trigger-release-flow-for-all-three-registries` (closed
  2026-05-11), which landed the `version:` input override.
- `release-yml-smoke-job-fails-on-tag-push-events` was parked on
  "human applies the proposed patch + verifies on a real release".
  The patch landed in `000708e` and was verified on v0.0.13; later
  refactored further in `68655f8` to the single-trigger flow. The
  smoke job today only runs on workflow_dispatch.

Closing them as part of this card's DoD removes the misleading
"6 active cards" reminder at session start.

## Implementation notes

- The bot's commit needs `contents: write` permission on the build
  job (already present today, used for the tag push). No new
  permissions required.
- The bot's commit will trigger a new push event on main. The CI
  workflow (`ci.yml`) runs `goc validate` and the asset-sync
  check on every push — the bot's release commit should pass both,
  because the rewrite scripts already keep the asset mirrors in
  sync. If the CI run on the release commit fails, the release is
  already published to the three registries by then, so it's a
  "loud signal but not blocking" failure. Worth catching in a
  separate hardening card if it ever bites.
- `pre-commit` will not run on the bot's push (CI runs in GitHub
  Actions, not local pre-commit). The asset-sync hook still needs
  to be valid because the next human commit will trip it; the
  rewrite script always leaves the tree in a consistent state.

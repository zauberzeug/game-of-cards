---
title: release-tripwire-only-inspects-the-head-commit-for-version-literal-edits
summary: "The release workflow's version-literal tripwire diffs exactly `HEAD~1..HEAD`, but AGENTS.md claims it \"fails the build on any human commit that touches those six files\". On a main branch receiving autonomous deck commits every 12h, a human literal edit is almost never at HEAD at dispatch time — one bot commit on top and the guard passes. The guard only ever catches a literal edit sitting exactly at HEAD."
status: open
stage: null
contribution: medium
created: "2026-07-19T04:08:07Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, documentation]
definition_of_done: |
  - [ ] PROCESS: decision recorded in `## Decision required` (deepen the diff range vs narrow the documented claim).
  - [ ] MECHANICAL: `.github/workflows/release.yml` tripwire step, its header comment, and the AGENTS.md tripwire sentence agree after the change (workflow edits require a maintainer session — the autonomous bot's `GITHUB_TOKEN` cannot touch `.github/workflows/`).
  - [ ] TDD: `uv run python .game-of-cards/deck/release-tripwire-only-inspects-the-head-commit-for-version-literal-edits/reproduce.py` exits zero (updated to assert the decided contract if the claim is narrowed instead of the range deepened).
  - [ ] TDD: if the range is deepened — a sandbox test demonstrates the guard catches a literal edit buried under later unrelated commits.
---

# The release tripwire only inspects the HEAD commit for version-literal edits

## Location

- `.github/workflows/release.yml` (tripwire step, "Tripwire — release
  commit must not edit version literals") —
  `diff=$(git diff --name-only HEAD~1 HEAD -- $tracked)` is the sole
  depth of the check.
- Same step's header comment — a human who "pushes a literal-bumping
  commit to main and then dispatches (release mode)" will "fail
  loudly".
- `AGENTS.md`, release section — "the in-job tripwire fails the build
  on any human commit that touches those six files".

## What's broken

The implementation diffs exactly one commit. If anything lands after
the human's literal edit — and this repo's autonomous pull-card /
audit-deck / refine-deck workflows commit deck cards to main on a
12h/2d cadence, so something nearly always does — the guard prints
`OK — HEAD leaves version literals alone.` and passes. The exemption
path compounds the gap: when HEAD *is* the previous bot release
commit, the whole check is skipped (`exit 0`), so the only case the
guard actually catches is a literal-editing commit sitting exactly at
HEAD at dispatch time. The documented enforcement scope ("any human
commit") would require diffing from the last bot release commit (or
last release tag) to HEAD.

## Empirical evidence

`uv run python .game-of-cards/deck/release-tripwire-only-inspects-the-head-commit-for-version-literal-edits/reproduce.py`:

```
release.yml tripwire uses depth-1 range ('git diff --name-only HEAD~1 HEAD -- ...'): True
tripwire's own range (HEAD~1..HEAD) sees: '' -> verdict: 'OK — HEAD leaves version literals alone.'
range covering every commit since baseline sees: 'claude-plugin/.claude-plugin/plugin.json'
FAIL: a human version-literal commit one position below HEAD passes the tripwire, contradicting AGENTS.md ('fails the build on any human commit that touches those six files')
[exit 1]
```

## Why it matters

The tripwire is the enforcement mechanism for "the workflow IS the
version writer" — the policy that keeps the six version-literal
surfaces consistent and keeps `tests/test_version_surfaces.py` green
across releases. A guard that passes whenever the offending commit is
not exactly at HEAD provides near-zero enforcement on this repo's
actual main-branch traffic (autonomous deck commits land far more
often than releases are dispatched). The release rewrite itself later
corrects the literals, so shipped artifacts stay right — the harm is
that the policy's loud-failure promise is quietly not kept, and a
human bump-and-tag habit could re-establish itself unnoticed.

## Decision required

1. **Deepen the range** — diff from the last bot release commit
   (author `github-actions[bot]`, subject
   `release: bump version literals to v*`) or the last `v*` tag to
   HEAD, excluding bot release commits themselves. Matches the
   documented "any human commit" scope. Slightly more complex shell;
   must handle first-release (no prior bot commit/tag) gracefully.
2. **Narrow the claim** — keep depth-1 and reword AGENTS.md plus the
   step's header comment to say the tripwire only checks the dispatch
   HEAD commit. Honest but weakens the policy to near-advisory.

Either way the fix touches `.github/workflows/release.yml`, which the
autonomous bot cannot edit — a maintainer session must land it (same
constraint that put the porter drift guard in a test, per AGENTS.md).

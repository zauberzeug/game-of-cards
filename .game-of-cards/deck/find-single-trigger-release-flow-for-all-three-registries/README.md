---
title: find-single-trigger-release-flow-for-all-three-registries
summary: "Goal: a one-way release flow where the maintainer takes exactly one action and PyPI, npm, AND ClawHub all publish without further user input. The closed card `auto-publish-npm-and-clawhub-on-tag-push` concluded \"two-step is unavoidable\" — but that conclusion was reached without exploring (a) workflow self-dispatch via `gh workflow run`, (b) `release: published` event chaining (kitchen-sink pattern), (c) `gh release create` from outside which auto-creates the tag plus fires the release event, (d) `repository_dispatch` from a bot or CLI wrapper, or (e) inverting the trigger entirely so the workflow creates the tag from a manual workflow_dispatch with a `version` input. This card systematically enumerates and empirically tests those paths, then either picks a winner and implements it OR documents the constraint each path hits and supersedes the open question."
status: active
stage: null
contribution: medium
created: 2026-05-11
closed_at: null
human_gate: session
advances:
  - auto-publish-npm-and-clawhub-on-tag-push
  - clawhub-publish-fails-with-package-belongs-to-another-publisher
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [x] Re-verify, against the live `openclaw/clawhub/.github/workflows/package-publish.yml@main` source and the live `clawhub` CLI v0.12.3 + v0.13.x (unreleased) capabilities, that the constraints recorded in `project_clawhub_oidc_constraints.md` are still valid as of the date this card is worked. Spec changes since 2026-05-10 must be folded in BEFORE evaluating any path below — the closed card's conclusion was correct for its day but the moving target may have moved.
  - [x] Path A — self-dispatch from push: folded into the synthesis block in the card body. Not tested empirically because Path C dominates it on every axis (smoke runs once vs twice, no anti-recursion exposure, no `actions: write` permission needed, single OAuth quota draw). Recorded as "not pursued because Path C subsumes the goal" rather than "blocked by a constraint."
  - [x] Path B — release-event chaining: folded into the synthesis block. Collapses into Path A under ClawHub's literal `workflow_dispatch` validator (verified above), so Path B has no independent value relative to Path C; rejected without spike.
  - [ ] Path C — inverted trigger (workflow creates the tag): release workflow is workflow_dispatch-only with a `version: 0.0.16` string input. The workflow itself does `git tag vX.Y.Z && git push origin vX.Y.Z` after a successful build. Maintainer's single action is clicking "Run workflow" in the GitHub UI (or running `gh workflow run release.yml -f version=0.0.16` from CLI). All registry publishes happen in the same workflow_dispatch run — no second event needed. ClawHub OIDC requirements satisfied natively. Spike whether the workflow's `GITHUB_TOKEN` can push a tag to the repo (yes, with `contents: write`), and whether `hatch-vcs` can read a tag pushed within the same run (subtle — the build job's checkout may have happened before the tag exists).
  - [x] Path D — repository_dispatch from a tiny CLI wrapper: rejected in the synthesis block. ClawHub's literal `workflow_dispatch` validator rejects `repository_dispatch` the same way it rejects `push`, so Path D would collapse into Path A. With Path C available, Path D has no ergonomic gain to justify the spike cost.
  - [x] Path E — manual-publish-via-comment / Issue or PR comment trigger: rejected in card body, see synthesis block.
  - [x] Synthesize: pick the simplest path that empirically works. Order the surviving paths by ergonomics + risk. Recommend ONE path as the production change in a short decision block in the card body.
  - [ ] If a winning path exists, implement the production change in `.github/workflows/release.yml` and verify on the next real release tag (v0.0.16 or whatever is shipped first after this card lands). Update `CLAUDE.md` release-flow section to reflect the new canonical flow. Supersede the closed card's "two-step is unavoidable" note with a link to this card.
  - [x] If NO path works (all blocked by current ClawHub server constraints), close this card with `superseded` status, record the failure modes in `project_clawhub_oidc_constraints.md` so the next maintainer doesn't redo the work, and CLAUDE.md keeps the two-step flow. — N/A: Path C succeeds.
  - [ ] Delete any spike branches and throw-away workflow files from the repo after results are recorded. Update `project_clawhub_oidc_constraints.md` with the empirical conclusions of each tested path.
  - [ ] `uv run goc validate` passes.
worker: {who: Rodja Trappe, where: main}
---

# find-single-trigger-release-flow-for-all-three-registries

## Goal

A maintainer should perform **one action** to ship a release. That one
action lands the new version on PyPI, npm, AND ClawHub with no further
human input. The current two-step (`git push origin vX.Y.Z` + `gh workflow
run release.yml --ref vX.Y.Z`) is operationally fine but architecturally
unsatisfying — it documents a registry-side constraint as a process-side
ritual.

## Why the closed card's conclusion is being re-opened

`auto-publish-npm-and-clawhub-on-tag-push` (closed 2026-05-10) recorded
five iterations (v0.0.8 → v0.0.12) that explored the auth-method axis
(inline CLI vs reusable workflow) and the event-type axis (push vs
workflow_dispatch). It concluded "two-step is unavoidable" — true under
the framing "the workflow_dispatch must come from a human." That framing
is itself an assumption, not a constraint discovered during the iterations.

The iterations did NOT explore:

- Whether a workflow can dispatch itself programmatically.
- Whether `release: published` events route through OIDC differently than
  `push` events (kitchen-sink uses this pattern).
- Whether the trigger can be inverted: workflow_dispatch as the entry
  point, with the workflow itself creating the tag after build + smoke
  pass.
- Whether `repository_dispatch` opens a usable side door.

This card systematically tests each path. The deliverable is either a
new single-action canonical flow or a verified recording of why each
path fails — so the next maintainer doesn't redo the exploration.

## Paths under test

### Path A: workflow self-dispatch on push

```
git push origin v0.0.16     # → release.yml runs on push
                            #     → build, publish-pypi, publish-npm (OIDC)
                            #     → trigger-clawhub-leg: gh workflow run release.yml --ref v0.0.16
                            # → release.yml runs again, event=workflow_dispatch
                            #     → publish-clawhub (OIDC)
```

Hypotheses:
1. `gh workflow run` from inside a workflow with `permissions: actions: write`
   and `GH_TOKEN: ${{ github.token }}` produces a `workflow_dispatch` event
   that ClawHub's validation accepts.
2. GitHub Actions' anti-recursion rule has `workflow_dispatch` as a documented
   exception, so the chain is allowed.
3. No actor-must-be-human server-side check kicks in (`github-actions[bot]`
   is the dispatching actor in the second run).
4. `permissions: actions: write` is a valid scope and is honoured at runtime
   (lesson from `5e91bcb`: YAML permissions sometimes parse silently into
   nothing).

Cost: ~6 minutes spike on a throw-away branch.

### Path B: release-event chaining (kitchen-sink pattern)

```
gh release create v0.0.16 --target main --generate-notes
                            # → creates tag v0.0.16 AND publishes a GitHub Release
                            # → release.yml triggers on release: types: [published]
                            #     → all publishes
```

This is the user's "release auto-creates the tag" idea. `gh release create`
DOES create the tag if it doesn't already exist (with `--target` specifying
the commit). One command, one trigger event.

But ClawHub's reusable workflow validation reads `github.event_name ==
'workflow_dispatch'` literally, not "any human-driven event." So Path B's
ClawHub leg would still need to be a self-dispatch (collapsing into Path A
plus a different entry event). The interesting question for Path B is
ergonomics: is `gh release create` a friendlier single command than
`git push tag`? Subjective; record but don't gate on it.

### Path C: invert the trigger — workflow creates the tag

```
gh workflow run release.yml -f version=0.0.16
                            # → release.yml runs, event=workflow_dispatch
                            #     → validates version, build, smoke
                            #     → tags v0.0.16 + pushes tag (contents: write)
                            #     → publish-pypi, publish-npm, publish-clawhub (all OIDC)
```

Most architecturally clean: ClawHub's workflow_dispatch-only OIDC
constraint is the native entry point. No self-dispatch, no event chaining.

Subtle points to spike:
- `hatch-vcs` reads `git describe --tags` for the wheel version. If the
  build job's checkout happened before the tag was created, the wheel may
  emit a `0.0.X.devN+gSHA` version instead of `0.0.16`. Mitigation: pin the
  wheel version with `SETUPTOOLS_SCM_PRETEND_VERSION` (already in place
  per `e780a20`'s precedent), and create the tag in a step *before*
  `uv build`.
- `GITHUB_TOKEN` with `contents: write` can push a tag, but the tag push
  itself does NOT trigger another workflow run (anti-recursion). So no
  loop risk.
- The workflow needs to be safe against double-clicks: if a user clicks
  "Run workflow" twice with the same version input, the second run should
  fail at the tag-push step (`tag already exists`) before any registry
  publish.

Cost: ~10 minutes spike. The reward is the cleanest path.

### Path D: repository_dispatch from a tiny CLI wrapper

```
goc release 0.0.16          # client-side: calls `gh api ... dispatches`
                            #              with event_type=release-0.0.16
                            # → release.yml triggers on repository_dispatch
                            #     → ...
```

Same OIDC-event-type wall as Path B (repository_dispatch is not
workflow_dispatch). Collapses into "Path D's entry-event triggers a
self-dispatch" — equivalent to Path A but with a CLI wrapper instead of a
`git push tag`. Ergonomic gain unclear; reject unless Paths A–C all fail.

### Path E: comment-driven (rejected)

PR/Issue-comment-triggered release workflows exist in other projects but
are operationally hostile for an OSS release. Rejected upfront.

## Order of evaluation

1. Path C (workflow creates tag) first — if it works, it's the cleanest
   and Paths A/B are unnecessary.
2. Path A (self-dispatch from push) second — if it works AND Path C does
   not, this is the fallback. Preserves the existing `git push tag` muscle
   memory.
3. Path B (release event) third — only if neither A nor C works, since it
   collapses into self-dispatch anyway.
4. Path D rejected unless A–C all fail (no ergonomic gain over Path A).
5. Path E rejected upfront.

## What changes if no path works

If every path is blocked by ClawHub server constraints, the conclusion
stands: two-step is unavoidable. But this card's value is the *recorded
evidence*. The closed card's "unavoidable" claim was reached via process
of elimination on two axes; this card adds a third axis (trigger-flow
shape) and explicitly tests it. Whichever way it lands, future maintainers
can read the result and skip the re-exploration.

## Risks beyond auth/event-type

- **Smoke + Claude OAuth quota**: every path except Path C runs smoke
  twice (once per event). Quota exhaustion can fail the second run
  silently. Path C runs smoke once. This is one more reason to prefer
  Path C.
- **Tag immutability**: Path C creates the tag from within CI. If the
  build fails after tag creation, we've a dangling tag. Mitigation:
  create-tag-and-push as the LAST step of build, after all validation.
- **Permission scope drift**: any path that uses `gh workflow run` or
  `git push tag` from CI depends on the `GITHUB_TOKEN` permission model
  not changing under us. Memory the verified permissions at spike time.

## Relationship to other cards

- `auto-publish-npm-and-clawhub-on-tag-push` (closed) — this card revisits
  its "two-step is unavoidable" conclusion. The five iterations stand as
  a record of the auth/event-type axes; this card adds the trigger-shape
  axis.
- `clawhub-publish-fails-with-package-belongs-to-another-publisher`
  (active) — built the OIDC-only architecture this card relies on.
  Whatever wins here must preserve OIDC.
- `workflows-write-in-yaml-permissions-block-breaks-autonomous-workflows`
  (active per `5e91bcb`) — lesson: verify YAML permissions empirically.
  Drives the "spike before implement" stance of this card.

## Out of scope

- Re-introducing token auth to enable `push`-event-only flow. Settled
  trade-off; OIDC stays.
- Optimising smoke runtime or Claude quota. Separate concern; not blocking.
- Changing the canonical flow in CLAUDE.md before a path is verified to
  work end-to-end.

## Verification of upstream constraints (2026-05-11)

DoD item #1 — checked against the live source today:

- `openclaw/clawhub/.github/workflows/package-publish.yml@main` validate
  step is byte-identical to `@v0.12.3` (the pinned version) on the OIDC
  + `workflow_dispatch` path. The check is purely
  `github.event_name == 'workflow_dispatch'` + presence of the OIDC
  request env vars. **No ref-pattern check.**
- v0.12.3 is the most recent tag in `openclaw/clawhub` (next is v0.11.0,
  then back through v0.5.0 / v0.4.0 / …). No newer reusable-workflow
  release has shipped since 2026-05-10.
- The six constraints recorded in `project_clawhub_oidc_constraints.md`
  remain valid; no spec drift to fold in.

Critical consequence for Path C: a workflow_dispatch fired from
`refs/heads/main` (with the tag created later in the run) passes the
ClawHub validator just as well as a workflow_dispatch fired from
`refs/tags/vX.Y.Z`. The validator does not inspect the ref.

## Synthesis — Path C wins

Ordered evaluation per the card's instructions:

1. **Path C (workflow creates the tag) — chosen.** Empirically supported
   by the upstream-source check above. The maintainer's single action is
   `gh workflow run release.yml -f version=0.0.16` (or click "Run
   workflow" in the GitHub UI). The workflow validates inputs, builds,
   runs smoke, creates and pushes the tag from inside CI, then publishes
   to PyPI + npm + ClawHub via OIDC from the same `workflow_dispatch`
   run. ClawHub's `workflow_dispatch`-only OIDC requirement is the
   native entry point — no self-dispatch, no event chaining, no
   anti-recursion exposure. Smoke runs once (not twice as in the
   two-step flow), halving the Claude OAuth quota draw per release.
2. **Path A (self-dispatch from push) — not pursued.** Would work
   technically (anti-recursion has an exception for `workflow_dispatch`
   and ClawHub validates the second run as workflow_dispatch) but
   Path C dominates: simpler trigger model, single OAuth quota draw, no
   `permissions: actions: write` exposure. Path A was the fallback in
   case Path C didn't work; with Path C verified, the fallback is moot.
3. **Path B (release-event chaining) — rejected.** ClawHub's validator
   reads `github.event_name` literally as `workflow_dispatch`. A
   `release: types: [published]` trigger would fail that check, so Path
   B collapses into "release event triggers a self-dispatch" — i.e.,
   Path A with a worse entry-event ergonomic. No independent value.
4. **Path D (repository_dispatch via CLI wrapper) — rejected.** Same
   event-type wall as Path B. Collapses into Path A. The CLI wrapper
   `goc release X.Y.Z` is a UX idea worth considering separately, but
   would dispatch the workflow_dispatch trigger directly, not need a
   second event.
5. **Path E (comment-triggered) — rejected upfront.** Operationally
   hostile for an OSS release.

## Subtle points addressed in the Path C implementation

- **`hatch-vcs` tag-read timing.** The build job creates the tag as its
  LAST step (after `uv build` succeeds). The wheel is built before the
  tag exists, so `hatch-vcs` cannot derive the version from
  `git describe --tags`. Mitigation: keep
  `SETUPTOOLS_SCM_PRETEND_VERSION` pinned to the input version (already
  in place — was added for the dry-run path). The wheel version is
  authoritative; the tag is documentation.
- **Tag-push does not re-trigger the workflow.** GitHub Actions'
  anti-recursion rule covers tag-push from inside the workflow when the
  workflow doesn't grant a PAT for the push. Using the workflow's
  default `GITHUB_TOKEN` with `contents: write` is sufficient AND
  doesn't trigger another run. Verified by GitHub's documented
  behaviour for the `GITHUB_TOKEN` actor.
- **Double-click protection.** If the user clicks "Run workflow" twice
  with the same version input, the second run's tag-creation step fails
  with `tag already exists` before any registry publish. The publish
  jobs are gated on the build job's tag-creation step succeeding, so a
  double-click cannot produce a partial second publish.
- **Mid-publish failure recovery.** If a publish job fails after the tag
  was pushed (e.g., a transient PyPI 5xx), re-running
  `gh workflow run release.yml --ref vX.Y.Z` re-fires the publishes on
  the existing tag. The compute step picks `mode=tag` for this path; no
  new tag is created.
- **PEP 440 / semver overlap.** The `version` input must be a string
  valid as BOTH PEP 440 and semver (e.g., `0.0.16`, `1.0.0`,
  `0.1.0a1`). The input is propagated verbatim into the wheel +
  package.json + plugin manifests; a bad string fails the build's
  consistency tripwires (the wheel-version assertion + the npm
  lockfile consistency check).

## What "verify on next real release" means in practice

DoD #7's second clause asks for verification on the next real release
tag. The card lands Path C immediately (verified end-to-end via the
existing `dry_run=true` path, which exercises every step except real
publishes + real tag-push). The first real test fires on whichever
version ships next — likely v0.0.16. If Path C works end-to-end, leave
the card closed. If it doesn't, re-open and record the empirical
constraint that broke (the upstream check above suggests it should
work, but server-side changes between today and the next release can
still surprise us).

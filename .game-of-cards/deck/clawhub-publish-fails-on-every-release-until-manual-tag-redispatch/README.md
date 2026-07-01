---
title: clawhub-publish-fails-on-every-release-until-manual-tag-redispatch
summary: "Since the ref:tag ClawHub fix landed (commit 3167525, just after v0.0.24), the ClawHub publish leg fails on every new-release dispatch from main: ClawHub's OIDC trusted-publish requires the published source commit to equal the OIDC-verified dispatch SHA, but the workflow publishes the bot's post-rewrite tag commit while the OIDC token is minted for the pre-rewrite main HEAD. v0.0.25 needed a manual `--ref v0.0.25` re-dispatch to ship ClawHub. Fix: release.yml self-dispatches a clawhub-only run on the freshly-pushed tag (GITHUB_TOKEN + actions:write, no PAT), so the OIDC sha equals the tag commit — no trusted-publisher reconfiguration because the entry filename stays release.yml."
status: done
stage: null
contribution: high
created: "2026-06-26T15:30:45Z"
closed_at: "2026-07-01T05:14:16Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] MECHANICAL: after build+smoke succeed, a new `redispatch-clawhub` job in `release.yml` self-dispatches `release.yml` on the release tag with `clawhub_only=true`, using the default `GITHUB_TOKEN` with `permissions: actions: write` (no PAT)
  - [x] MECHANICAL: in `clawhub_only` mode the run skips `smoke`, `publish-pypi`, and `publish-npm`, and `publish-clawhub` runs (accepting a skipped smoke); the from-main `release`-mode run no longer runs `publish-clawhub` directly and stays green
  - [x] MECHANICAL: no infinite re-dispatch — `redispatch-clawhub` only fires in `mode == release` (the tag-triggered `clawhub_only` run is `mode == tag`, so it does not re-dispatch)
  - [x] PROCESS: no ClawHub trusted-publisher reconfiguration required — the entry workflow filename stays `release.yml` (ClawHub pins the caller filename via the OIDC `workflow_ref` claim, not the ref); AGENTS.md release section documents the auto-dispatch and the `-f clawhub_only=true` manual recovery
  - [x] TDD: `tests/test_release_workflow_clawhub_source_ref.py` extended to assert the redispatch job, its `actions: write` permission + tag self-dispatch, the `clawhub_only` gating of smoke/pypi/npm, and that publish-clawhub no longer runs in `release` mode
  - [x] EMPIRICAL: proven end-to-end by v0.0.26 — a single `gh workflow run release.yml -f version=0.0.26` from main published all three registries with ClawHub going GREEN via the automatic `clawhub_only` tag re-dispatch (stronger than merely clearing `resolveTrustedPublishSource`; zero manual steps, unlike v0.0.25). The fix adds no actionlint regression: `actionlint release.yml` reports only 3 pre-existing style/info shellcheck findings (SC2001/SC2086 at L269/L273/L492 in the version-tripwire and Path-A steps, last touched 2026-05, unrelated to this card)
worker: {who: Rodja Trappe, where: fix/clawhub-publish-from-release-tag}
---

# ClawHub publish fails on every release until a manual tag re-dispatch

## Symptom

A normal release dispatch — `gh workflow run release.yml -f version=X.Y.Z`
from `main` — publishes PyPI and npm but the **ClawHub leg fails**:

```
Error: Trusted publish source commit must match the verified GitHub SHA
    at resolveTrustedPublishSource (../convex/packages.ts:7165)
```

The release is only completable by a second, manual dispatch from the
tag (`gh workflow run release.yml --ref vX.Y.Z`), which is how v0.0.25
was shipped. This recurs on **every** release.

## Root cause

This is self-inflicted, not a ClawHub-side change. The commit guard
(`source.commit !== publishToken.sha`) has existed server-side since at
least 2026-06-08. What changed is **our** wiring:

- v0.0.24 (tag commit 2026-06-08 03:18) shipped with the *old* ClawHub
  wiring, which published from the workflow-dispatch SHA. That SHA
  equalled the OIDC-verified `sha`, so the commit guard passed — but the
  bundled `openclaw-plugin/package.json` was the stale pre-rewrite copy
  (the bug fixed by `clawhub-package-publishes-pre-rewrite-package-json`).
- Commit `3167525` ("fix(release): publish clawhub from release tag",
  2026-06-08 06:20 — *after* v0.0.24 tagged) made ClawHub fetch package
  files from `ref: vX.Y.Z`, the bot's post-rewrite tag commit. That
  fixed the stale-payload bug but means the published `source.commit`
  (resolved from the tag) now differs from the OIDC `sha` (the
  pre-rewrite `main` HEAD at dispatch).
- v0.0.25 is the **first** release to exercise the `ref:tag` wiring, so
  it is the first to trip the commit guard.

The constraint that makes a single from-main dispatch impossible:

- The OIDC token's `sha`/`ref` claims are frozen to the **dispatch**
  event. A `workflow_dispatch` from `main` always claims the pre-rewrite
  `main` HEAD, never the new tag commit the build job creates mid-run.
- ClawHub OIDC trusted publishing accepts **only** `workflow_dispatch`
  events (server hard-rejects `push`/`release`), so a tag-push trigger
  is not an option.

## Fix

Publish ClawHub from a `workflow_dispatch` run **triggered on the tag**,
so the OIDC `sha` *is* the tag commit. `release.yml` does this itself:

1. New input `clawhub_only` (boolean, default false).
2. New job `redispatch-clawhub` (`needs: [build, smoke]`,
   `if: mode == release && !dry_run && !clawhub_only`,
   `permissions: actions: write`) runs, after the tag is pushed and
   smoke passes: `gh workflow run release.yml --ref vX.Y.Z -f clawhub_only=true`.
3. The self-dispatched run is `workflow_dispatch` on `refs/tags/vX.Y.Z`
   → `mode == tag`, `clawhub_only == true`. It **skips** `smoke`,
   `publish-pypi`, `publish-npm`, and runs `publish-clawhub` with
   `ref: vX.Y.Z`. Now OIDC `sha` == the tag commit == the resolved
   `source.commit` → the guard passes.
4. `publish-clawhub` no longer runs in `mode == release`, so the from-main
   run stays green and ClawHub is delegated to the tag run.

Why this needs no new secret and no reconfiguration:

- **No PAT.** `workflow_dispatch` (and `repository_dispatch`) are the
  explicit exceptions to the rule that `GITHUB_TOKEN`-triggered events do
  not start new runs (GitHub changelog 2022-09-08). The default token
  with `permissions: actions: write` can self-dispatch a run that
  actually executes.
- **No ClawHub reconfiguration.** ClawHub's trusted-publisher record
  matches the **caller workflow filename** from the OIDC `workflow_ref`
  claim (`.../release.yml@<ref>`) and does **not** pin the ref. Keeping
  the publish in `release.yml` (only changing the triggering ref from
  `main` to the tag) keeps the registered identity intact. Moving it to
  a new file would require `clawhub package trusted-publisher set
  --workflow-filename <new>` and is therefore avoided.

## Recovery / manual path

If the auto-dispatched ClawHub run fails (or to re-publish), a maintainer
runs the clawhub-only path directly:

```bash
gh workflow run release.yml --ref vX.Y.Z -f clawhub_only=true
```

The older "re-run everything on the tag" recovery
(`gh workflow run release.yml --ref vX.Y.Z`) still works but re-runs
pypi/npm (which no-op or fail on the already-published version).

## Location

- `.github/workflows/release.yml` — `redispatch-clawhub` (new),
  `publish-clawhub` gating, `smoke`/`publish-pypi`/`publish-npm` gating,
  `clawhub_only` input
- `tests/test_release_workflow_clawhub_source_ref.py` — extended coverage
- `AGENTS.md` — release-section prose

## Verification

Confirmed end-to-end by the **v0.0.26** release (2026-07-01):

- A single `gh workflow run release.yml -f version=0.0.26` from `main`
  published **all three registries** — PyPI, npm, and ClawHub — with no
  manual step. Contrast v0.0.25, which needed a hand-run `--ref` tag
  re-dispatch that then collided with npm's already-published version.
- The from-main run (`28494572761`) stayed green: build → smoke → pypi +
  npm + `redispatch-clawhub`, while **skipping** `publish-clawhub`
  (`mode == release`). Its `redispatch-clawhub` job auto-dispatched a
  second run on tag `v0.0.26`.
- That tag run (`28494689798`, `clawhub_only=true`, `mode == tag`)
  skipped smoke/pypi/npm and published **ClawHub green** — not merely
  clearing `resolveTrustedPublishSource` but completing the publish,
  because the OIDC `sha` equalled the tag commit. It did **not**
  re-dispatch (no infinite loop).
- Registries independently confirmed live at `0.0.26`: PyPI + npm via
  registry JSON, ClawHub via the green publish job.
- `tests/test_release_workflow_clawhub_source_ref.py` — 6 tests green.
- `actionlint release.yml` reports only 3 pre-existing style/info
  shellcheck findings (SC2001/SC2086 at L269/L273/L492), untouched by
  this fix and unrelated to the ClawHub wiring.

---
title: auto-publish-npm-and-clawhub-on-tag-push
summary: "Extend `.github/workflows/release.yml` to auto-publish the OpenClaw plugin to npm AND ClawHub on every tag push, mirroring the existing PyPI OIDC trusted-publisher flow. Today PyPI is automated but npm + ClawHub are manual (`npm login` + interactive 2FA OTP + `clawhub login` + `clawhub package publish`). The 2FA wall hit during the v0.0.7 release proves the manual flow doesn't scale: every release demands the maintainer be at their authenticator. Both registries support OIDC-style trusted publishing — npm via id-token + provenance attestation; ClawHub via `clawhub package trusted-publisher` configured in the web UI — so we can ship token-free CI publishing on tag push."
status: active
stage: null
contribution: high
created: 2026-05-10
closed_at: null
human_gate: none
advances:
  - publish-openclaw-plugin
  - provide-openclaw-plugin-for-skills-and-hooks
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] `.github/workflows/release.yml` extended with a `publish-npm` job that runs on tag push, has `id-token: write` permission, runs `npm publish --provenance --access public` from `openclaw-plugin/`, and is gated on `build` + (where applicable) `smoke`
  - [ ] `.github/workflows/release.yml` extended with a `publish-clawhub` job that runs on tag push, calls `clawhub package publish ./openclaw-plugin --version <tag> --json` using the trusted-publisher OIDC flow (no `CLAWHUB_TOKEN` secret needed once the trusted-publisher is configured)
  - [ ] `release.yml` header comment documents the two new jobs and the trusted-publisher setup steps required on the npm side and ClawHub side
  - [ ] npm trusted publisher configured for `game-of-cards` at <https://www.npmjs.com/package/game-of-cards/access> — GitHub repo `zauberzeug/game-of-cards`, workflow `release.yml`, environment empty (or `pypi`-style) — recorded in this card's log when done
  - [ ] ClawHub trusted publisher configured for the `game-of-cards` package via the ClawHub web UI — same GitHub repo + workflow path — recorded in this card's log when done
  - [ ] First end-to-end auto-publish proven by tagging `v0.0.8` (or a `v0.0.7-test` pre-release) and observing all three registries (PyPI, npm, ClawHub) updated by CI alone
  - [ ] CLAUDE.md / AGENTS.md release-flow guidance updated: maintainers run `<bump versions> && git tag vX.Y.Z && git push origin vX.Y.Z` and that's it
  - [ ] `uv run goc validate` passes
worker: {who: Rodja Trappe, where: main}
---

# Auto-publish to npm + ClawHub on tag push

## Why

Today `release.yml` auto-publishes to PyPI on tag push (via OIDC trusted publishing — no token in the repo, just `id-token: write` permission). The OpenClaw plugin's npm + ClawHub publishes are still manual. That gap surfaced sharply during the v0.0.7 release:

- `npm publish --access public` was rejected with `403 Two-factor authentication or granular access token with bypass 2fa enabled is required to publish packages` — the maintainer's npm account has 2FA-on-publish enforced.
- The workaround is `--otp=XXXXXX` typed at the command line from the authenticator app, which means every release demands the maintainer be physically at their phone.
- Same for ClawHub: `clawhub login` is interactive (browser flow), and `clawhub package publish` runs from the maintainer's local machine.

Result: PyPI ships from CI on tag push, but npm + ClawHub require a synchronous maintainer presence. That's a regression from the PyPI flow's ergonomic baseline.

## Decision

Extend `release.yml` so a single `git push origin vX.Y.Z` triggers all three publishes (PyPI + npm + ClawHub) using OIDC-style trusted publishing on every channel — no long-lived secrets in repo settings, no maintainer presence required.

## Implementation plan

### 1. `publish-npm` job

```yaml
publish-npm:
  name: Publish to npm
  needs: [build, smoke]
  runs-on: ubuntu-latest
  if: ${{ startsWith(github.ref, 'refs/tags/v') && !inputs.dry_run && (needs.smoke.result == 'success' || needs.smoke.result == 'skipped') }}
  permissions:
    id-token: write   # OIDC for npm trusted publishing
    contents: read
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: '20'
        registry-url: 'https://registry.npmjs.org'
    - name: Install plugin deps
      working-directory: openclaw-plugin
      run: npm ci
    - name: Build dist
      working-directory: openclaw-plugin
      run: npm run build
    - name: Publish to npm with provenance
      working-directory: openclaw-plugin
      run: npm publish --provenance --access public
```

**npm trusted publisher setup** (one-time, in the npm web UI at <https://www.npmjs.com/package/game-of-cards/access>): add a trusted publisher entry pointing at:
- Owner: `zauberzeug`
- Repository: `game-of-cards`
- Workflow filename: `release.yml`
- Environment: `(none)` (or set to `pypi` to share the existing environment if desired)

Once configured, `npm publish` from the configured workflow uses OIDC instead of `NODE_AUTH_TOKEN`. The `--provenance` flag attaches a verifiable build attestation to the published tarball, visible on the npm package page.

### 2. `publish-clawhub` job

```yaml
publish-clawhub:
  name: Publish to ClawHub
  needs: [build, smoke]
  runs-on: ubuntu-latest
  if: ${{ startsWith(github.ref, 'refs/tags/v') && !inputs.dry_run && (needs.smoke.result == 'success' || needs.smoke.result == 'skipped') }}
  permissions:
    id-token: write   # OIDC for ClawHub trusted publishing
    contents: read
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: '20'
    - name: Install ClawHub CLI
      run: npm i -g clawhub
    - name: Build dist
      working-directory: openclaw-plugin
      run: |
        npm ci
        npm run build
    - name: Publish to ClawHub
      run: |
        version="${GITHUB_REF#refs/tags/v}"
        clawhub package publish ./openclaw-plugin \
          --version "$version" \
          --changelog "Automated release for v$version" \
          --json
```

**ClawHub trusted publisher setup** (one-time, in the ClawHub web UI for the `game-of-cards` package): mirror the npm config — point at the same GitHub repo + workflow path. After configuration, `clawhub package publish` from the matching workflow uses the OIDC token automatically; manual publishes from a maintainer machine then require `--manual-override-reason "..."` (which is fine — it's the safety rail that keeps drive-by publishes off the package).

### 3. `smoke` interaction

`release-yml-smoke-job-fails-on-tag-push-events` (parked at gate=session) already documents that `smoke` errors on push events. The chosen fix — narrow `smoke.if` to `workflow_dispatch` only, `(success || skipped)` in publish gate — is the same shape needed here. Land that fix in this card OR adopt its `(success || skipped)` gate language explicitly so the new jobs work on both the tag-push and workflow_dispatch paths. Recommend folding both fixes into this card's PR — they touch the same file and share the same gate logic.

## Why trusted-publisher OIDC over a long-lived token

| Concern | Long-lived `NPM_TOKEN` / `CLAWHUB_TOKEN` | OIDC trusted publisher |
|---|---|---|
| Compromise blast radius | High (full publish rights for the token's lifetime) | Low (token minted per-workflow-run, scoped to the configured repo+workflow only) |
| Rotation cadence | Maintainer must remember to rotate | Automatic — every CI run gets a fresh ephemeral token |
| Visibility into who published | Token name (often shared) | GitHub Actions run URL, signed attestation |
| Setup complexity | Generate token + add as repo secret + reference in workflow env | One-time web-UI configuration, no secret management |
| Provenance attestation | Optional / extra step | Native (`--provenance` on npm bakes the attestation into the tarball) |

## Scope boundaries

- This card sets up the auto-publish workflow and tells the human what trusted-publisher entries to create. The actual web-UI configuration is a manual step the maintainer does once per package — there is no API for "create a trusted publisher" on either npm or ClawHub.
- v0.0.7 itself stays as a manual publish (the OTP workflow already in motion is fine). The new CI flow proves itself on v0.0.8 or a pre-release.
- This is not a release-strategy change — `git tag vX.Y.Z && git push --tags` remains the trigger. It just makes more things happen on that trigger.

---
title: auto-publish-npm-and-clawhub-on-tag-push
summary: "Extend `.github/workflows/release.yml` to auto-publish the OpenClaw plugin to npm AND ClawHub on every tag push, mirroring the existing PyPI OIDC trusted-publisher flow. Today PyPI is automated but npm + ClawHub are manual (`npm login` + interactive 2FA OTP + `clawhub login` + `clawhub package publish`). The 2FA wall hit during the v0.0.7 release proves the manual flow doesn't scale: every release demands the maintainer be at their authenticator. Both registries support OIDC-style trusted publishing — npm via id-token + provenance attestation; ClawHub via `clawhub package trusted-publisher` configured in the web UI — so we can ship token-free CI publishing on tag push."
status: done
stage: null
contribution: high
created: 2026-05-10
closed_at: 2026-05-10
human_gate: none
advances:
  - publish-openclaw-plugin
  - provide-openclaw-plugin-for-skills-and-hooks
advanced_by:
  - publish-npm-package-under-zauberzeug-org-not-personal
  - find-single-trigger-release-flow-for-all-three-registries
tags: [story, infra]
definition_of_done: |
  - [x] `.github/workflows/release.yml` extended with a `publish-npm` job that runs on tag push, has `id-token: write` permission, runs `npm publish --provenance --access public` from `openclaw-plugin/`, and is gated on `build` + (where applicable) `smoke`
  - [x] `.github/workflows/release.yml` extended with a `publish-clawhub` job that runs on tag push, calls `clawhub package publish ./openclaw-plugin --version <tag> --json` using the trusted-publisher OIDC flow (no `CLAWHUB_TOKEN` secret needed once the trusted-publisher is configured)
  - [x] `release.yml` header comment documents the two new jobs and the trusted-publisher setup steps required on the npm side and ClawHub side
  - [x] npm trusted publisher configured for `game-of-cards` at <https://www.npmjs.com/package/game-of-cards/access> — Owner=zauberzeug, Repo=game-of-cards, Workflow=release.yml, Environment=npm
  - [x] ClawHub trusted publisher configured via `clawhub package trusted-publisher set game-of-cards --repository zauberzeug/game-of-cards --workflow-filename release.yml` (no environment — see below for why)
  - [x] First end-to-end auto-publish proven on v0.0.12 (PyPI + npm via tag-push, ClawHub via workflow_dispatch — see implementation history below for why two events)
  - [x] CLAUDE.md / AGENTS.md release-flow guidance updated: maintainers run `<bump versions> && git tag vX.Y.Z && git push origin vX.Y.Z` and that's it
  - [x] `uv run goc validate` passes
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

## Implementation status

The workflow file at `.github/workflows/release.yml` now defines four jobs gated on tag push: `build`, `smoke` (workflow_dispatch only), `publish-pypi`, `publish-npm`, and `publish-clawhub`. All three publish jobs use OIDC trusted publishing — `id-token: write` permission, no long-lived secrets in repo settings. The `publish-clawhub` job relies on the ClawHub CLI's native GitHub Actions OIDC support (verified by reading `node_modules/clawhub/dist/cli/commands/packages.js`: it detects `ACTIONS_ID_TOKEN_REQUEST_URL` + `ACTIONS_ID_TOKEN_REQUEST_TOKEN` and exchanges them for a publish token automatically).

Three GitHub environments are referenced (`pypi`, `npm`, `clawhub`) — each carries the trusted-publisher claim values that scope OIDC to this workflow. They're created automatically the first time a job that references them runs; the trusted-publisher entries on the registry side are what gate which workflow runs can mint tokens.

The fix from the parked card `release-yml-smoke-job-fails-on-tag-push-events` was folded in by the same release.yml rewrite — its proposed diff is now live: `smoke.if` narrowed to `${{ github.event_name == 'workflow_dispatch' }}` and the publish gates use the `always() && build==success && (smoke==success || smoke==skipped)` pattern that lets tag-push releases proceed past a skipped smoke job without smoke ever needing to run on the unsupported `push` event.

## Action required (gate session)

Two web-UI configurations stand between this card and a green end-to-end auto-publish:

1. **npm trusted publisher** — go to <https://www.npmjs.com/package/game-of-cards/access>, scroll to the "Trusted Publishers" section (or equivalent under "Manage Access"), add a new GitHub Actions trusted publisher with these claim values:
   - Owner: `zauberzeug`
   - Repository: `game-of-cards`
   - Workflow filename: `release.yml`
   - Environment: `npm`
2. **ClawHub trusted publisher** — at the package's ClawHub admin page (<https://clawhub.ai/packages/game-of-cards> → Settings → Trusted Publishers, or wherever the UI surfaces it), add a GitHub Actions trusted publisher with the same claim values except environment `clawhub`.

After both entries exist, cut v0.0.8:
1. Bump versions in `pyproject.toml`, `goc/__init__.py`, `openclaw-plugin/package.json`, `openclaw-plugin/package-lock.json`, `claude-plugin/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` (sync hook handles the engine-mirror copies).
2. `git commit -m "release: bump to 0.0.8" && git tag v0.0.8 && git push origin main && git push origin v0.0.8`.
3. Watch <https://github.com/zauberzeug/game-of-cards/actions> — `build` runs, `smoke` skips, all three publish jobs run in parallel, and v0.0.8 lands on PyPI, npm, and ClawHub within ~2 minutes with no further human input.

If any of the three publishes fail with an OIDC error, that's the corresponding registry rejecting the trusted-publisher claim — re-check the entry's owner/repo/workflow/environment match exactly.

## Postscript (2026-05-11) — single-trigger flow supersedes "two-step is unavoidable"

This card's implementation ended on a two-step flow: `git push tag` →
PyPI + npm via OIDC; `gh workflow run release.yml --ref vX.Y.Z` →
ClawHub via OIDC. That conclusion was framed around "the
workflow_dispatch must come from a human" — a framing assumption, not
a discovered constraint.

The follow-on card
`find-single-trigger-release-flow-for-all-three-registries` revisited
that assumption and found ClawHub's validator only checks
`github.event_name == 'workflow_dispatch'` (not the ref). So a
workflow_dispatch fired from `refs/heads/main` (the workflow then
creates and pushes the tag) satisfies the same validator a
workflow_dispatch from `refs/tags/vX.Y.Z` would. The canonical flow is
now:

```
gh workflow run release.yml -f version=X.Y.Z
```

The `push: tags:` trigger has been removed from `release.yml`. Tag-push
no longer triggers anything — the workflow only enters via
`workflow_dispatch`. See the follow-on card's body for the synthesis
and the constraint trail.

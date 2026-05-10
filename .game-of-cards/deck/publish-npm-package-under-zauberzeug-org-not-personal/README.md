---
title: publish-npm-package-under-zauberzeug-org-not-personal
summary: "Publish the `game-of-cards` npm package under Zauberzeug org ownership, not under the maintainer's personal npm account. Decision (2026-05-10): keep the unscoped name `game-of-cards` for parity with PyPI + ClawHub; org ownership is established via npm's owner/access controls rather than the package name. Bootstrap path: first-publish from the maintainer's personal account (npm requires the package to exist before owner transfers can happen), then `npm access grant` zauberzeug org as owner, then optionally remove personal account from owners. Trusted publisher entry is then configured by a zauberzeug org owner."
status: done
stage: null
contribution: medium
created: 2026-05-10
closed_at: 2026-05-10
human_gate: session
advances:
  - publish-openclaw-plugin
  - auto-publish-npm-and-clawhub-on-tag-push
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [x] zauberzeug npm org exists; current user is an org member (verified 2026-05-10 via `npm access list packages zauberzeug` returning the package)
  - [x] First publish of `game-of-cards@0.0.7` to npm completed under personal account `rodja` (verified live at <https://www.npmjs.com/package/game-of-cards>; sha256 matches local tarball)
  - [x] Org team granted write access: `npm access grant read-write zauberzeug:developers game-of-cards` (verified via `npm access list packages zauberzeug:developers` → `game-of-cards: read-write`). Note: for **unscoped** npm packages, this team grant — not the maintainer list — IS the org-level write-access mechanism. Orgs cannot appear in the `Maintainers:` list of an unscoped package; that's an npm-side limitation specific to unscoped naming. The team grant gives every member of `zauberzeug:developers` (including CI via OIDC if configured at the org level) publish rights.
  - [x] Personal account stays as the listed maintainer because npm refuses to remove the last maintainer of an unscoped package and orgs cannot be added as maintainers for unscoped names. The team-write grant is what gives the org publish ability; the visible-maintainer field remains a personal handle. Trade-off accepted: package-page metadata shows `rodja` as maintainer, while functional access control is org-level.
  - [x] npm trusted publisher entry configured at <https://www.npmjs.com/package/game-of-cards/access> — Owner=zauberzeug, Repo=game-of-cards, Workflow=release.yml, Environment=npm
  - [x] ClawHub equivalent: package `game-of-cards` is owned by `zauberzeug` ClawHub org (created via account settings on 2026-05-10); trusted publisher entry configured via `clawhub package trusted-publisher set` with no environment (the reusable workflow can't set job-level environment, so TP entry must not require one — see `auto-publish-npm-and-clawhub-on-tag-push` log for the full constraint stack)
  - [x] First end-to-end auto-publish proven on v0.0.12 — all three registries (PyPI, npm, ClawHub) published under zauberzeug org ownership via OIDC trusted publishing. PyPI + npm via tag-push; ClawHub via `gh workflow run release.yml --ref v0.0.12` (workflow_dispatch step required for ClawHub OIDC). Confirmed live on 2026-05-10: `npm view game-of-cards version` → 0.0.12, `pypi.org/.../json` → 0.0.12, `clawhub package inspect game-of-cards` → Latest: 0.0.12, Owner: zauberzeug
  - [x] `uv run goc validate` passes
worker: {who: Rodja Trappe, where: main}
---

# Publish npm package under Zauberzeug org, not personal account

## Why

The npm package `game-of-cards` should be visible as a Zauberzeug-published artifact, not as `rodja`'s personal package. This matters for:

- **Discoverability and trust signal.** Plugins published under an org name look like enterprise-backed artifacts; plugins published under a personal handle look like side projects. The OpenClaw plugin is positioned as a Zauberzeug-supported artifact, so the npm metadata should reflect that.
- **Continuity.** If the original publisher's npm account changes (employer, identity, security incident), org-owned packages keep working without an emergency ownership transfer under stress.
- **Multi-maintainer access.** Org-owned packages let any org member publish or manage releases without the bus-factor of a single account.

## Naming decision (2026-05-10)

**Chosen: unscoped `game-of-cards`, owned by zauberzeug org.**

Rejected: scoped `@zauberzeug/game-of-cards`. The scoped form is more idiomatic for org-owned npm packages, but it would break name parity with PyPI (`game-of-cards`) and ClawHub (`game-of-cards`). The single-name-everywhere experience is worth more than scoped-form idiom in this case — discovery flows like "find this package on every registry I'm familiar with" stay frictionless.

Trade-off accepted: org ownership is signaled via npm's owner/access metadata, not the package name itself. Users skimming `npm install game-of-cards` won't see "@zauberzeug" on the install line; they'll see it on the package page (<https://www.npmjs.com/package/game-of-cards>) and in the maintainer/owner list.

## Bootstrap path (chicken-and-egg unblock)

npm's trusted-publisher UI requires the package to exist before it appears. Same for the org-ownership transfer commands. So the first publish has to go through the maintainer's personal account, after which everything else can be done.

```
# Step 1: Verify or create the zauberzeug npm org (free for public packages).
#   https://www.npmjs.com/org/create

# Step 2: First publish from personal account (needs OTP or bypass-2fa token).
cd openclaw-plugin
npm publish --access public --otp=<6-digit code>
# OR via granular access token with bypass-2fa:
#   npm set //registry.npmjs.org/:_authToken=npm_XXXX
#   npm publish --access public
#   npm config delete //registry.npmjs.org/:_authToken

# Step 3: Grant the zauberzeug org's developers team read-write on the package.
# (The 'developers' team must already exist in the org; npm orgs ship with
# 'developers' by default. Substitute another team name if your org's structure
# differs.)
npm access grant read-write zauberzeug:developers game-of-cards

# Step 4: REMOVED — `npm owner add <orgname>` does NOT work for unscoped packages
# (npm treats orgs as non-users and the request 404s). The team-write grant in
# step 3 is the org-access mechanism; the maintainer list will continue to show
# the personal handle, which is an npm-side limitation specific to unscoped
# names. To get a singular org-as-owner display, the package must be scoped
# (`@zauberzeug/game-of-cards`) — see the naming-decision section above for
# why we chose unscoped despite this trade-off.

# Step 5: configure trusted publisher in the npm web UI (now visible because
# the package exists). Sign in as a zauberzeug org owner; navigate to
#   https://www.npmjs.com/package/game-of-cards/access
# → Trusted Publishers → add GitHub Actions claim:
#     Owner: zauberzeug
#     Repo:  game-of-cards
#     Workflow: release.yml
#     Environment: npm
```

After step 5, the existing `release.yml` workflow auto-publishes on tag push without any further human action — the OIDC handshake mints a per-run publish token scoped to the configured (repo, workflow, environment) tuple.

## ClawHub side

ClawHub uses owner/handle ownership rather than scoped names. The first `clawhub package publish` from `@rodja` would publish under the personal handle. To put the package under a zauberzeug-aligned handle:

- If a `zauberzeug` ClawHub handle/org exists or can be created, publish under that handle from the start (the `--owner <handle>` flag on `clawhub package publish` is admin-only — the cleaner path is to log in as that handle and publish directly).
- If only a personal handle is feasible today, publish under personal first, then file a follow-up to transfer ownership when ClawHub adds an ownership-transfer flow (the CLI doesn't currently expose a `clawhub package transfer-ownership` verb).

The ClawHub trusted publisher entry is configured by whichever ClawHub identity owns the package, mirroring the npm pattern.

## Why this isn't `auto-publish-npm-and-clawhub-on-tag-push`

That sibling card (status=blocked, gate=session) is about the workflow file existing and being correctly configured. This card is about *which identity* owns the package on the registry — a separate concern that's a precondition for the trusted publishers in that card to even be configurable. They form a chain:

1. **This card**: bootstrap first-publish under correct ownership.
2. **`auto-publish-npm-and-clawhub-on-tag-push`**: workflow file exists (already done, just waiting on trusted publisher entries).
3. Configure trusted publisher entries → auto-publish works on every tag push.

Both DoDs converge on the same v0.0.8 verification — once both close, releases are fully automated.

## Scope boundaries

- This card does NOT cover the workflow file changes (those are in `auto-publish-npm-and-clawhub-on-tag-push`, already complete).
- This card does NOT publish v0.0.7 yet — it documents the path. Actual publish is a maintainer action under their npm credentials.
- If creating the zauberzeug npm org turns out to require a paid plan (org pricing changes occasionally), pause and re-evaluate: scoped `@zauberzeug/game-of-cards` becomes the better path because scopes are free for public packages even on the free tier.

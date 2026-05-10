# 2026-05-10 — investigation: token-override path is the trigger, OIDC path is the fix

Compared the failed v0.0.13 publish command (run `25629654305`, job `75231120722`)
with the most recent successful publish (run `25623831354`, job `75215406764`,
which published v0.0.12 at 08:16Z on `main`):

**Failed (13:13Z)**
```
bun .../cli.ts package publish zauberzeug/game-of-cards@dacd7ee... \
  --json --tags latest --source-ref refs/tags/v0.0.13 \
  --source-path openclaw-plugin \
  --manual-override-reason 'GitHub Actions workflow_dispatch publish via CLAWHUB_TOKEN'
```

**Succeeded (08:16Z, same day)**
```
bun .../cli.ts package publish zauberzeug/game-of-cards@84f73a4... \
  --json --tags latest --source-ref refs/heads/main \
  --source-path openclaw-plugin
```

The only meaningful difference is `--manual-override-reason`. The reusable
workflow at `openclaw/clawhub/.github/workflows/package-publish.yml@v0.12.3`
chooses the token-override path whenever `clawhub_token` is supplied, otherwise
falls back to OIDC trusted publishing using the runtime audience
`clawhub-workflow-source`.

`gh secret list` shows `CLAWHUB_TOKEN` was last updated at `2026-05-10T08:34:09Z`
— **between the 08:16Z success and the 11:55Z failure.** Before that update the
secret was effectively absent for the OIDC path's purposes (the workflow's
"No ClawHub token provided; publish will rely on GitHub OIDC trusted
publishing" branch fired at 08:16Z, hence the missing override flag).

`clawhub package inspect game-of-cards` confirms the package's `owner.handle`
is `zauberzeug` and the `verification.tier` is `source-linked`, with
`sourceCommit: 84f73a4...` and `sourceTag: refs/heads/main` — the v0.0.12
artifact published in the 08:16Z run.

## Anti-evidence resolved

Hypothesis from the original card body — "npm-org rebrand re-anchored the
publisher identity" — is **falsified**. The package `owner` is already
`zauberzeug`, set when 0.0.12 was published via OIDC on 2026-05-10T08:16Z
under the OIDC publisher = the GitHub repo identity. The npm-org rebrand
did not touch ClawHub state.

Real root cause: ClawHub's Convex store records the publisher identity that
**first registered each package**. v0.0.12 was registered under the OIDC
identity (the GitHub repo). Subsequent publishes via the token-override path
present a different identity (whatever account ran `clawhub login` to
generate the token), which the store rejects with the seen `Package already
exists and belongs to another publisher` error.

## Fix path

Drop `clawhub_token` from the `secrets:` block of the `publish-clawhub` job
in `.github/workflows/release.yml`. With no token supplied, the reusable
workflow falls through to the OIDC path that registered the package and
authenticates as the same identity. Trade-off: tag-push events lose their
ClawHub publish, but they were already losing the publish to the
`release-yml-smoke-job-fails-on-tag-push-events` bug; the documented
recovery (`gh workflow run release.yml --ref vX.Y.Z`) is workflow_dispatch
on a tag, which OIDC supports.

After the workflow change merges, also delete or empty the `CLAWHUB_TOKEN`
secret so a future maintainer doesn't reintroduce the override path by
accident.

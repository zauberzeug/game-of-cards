
## 2026-05-10 — Five-iteration learning curve, end state captured

The DoD ticked at v0.0.12 after a sequence of failed iterations on v0.0.8 → v0.0.11. Each release surfaced a different ClawHub trusted-publishing constraint that wasn't documented anywhere except in server error messages. Recorded for future maintainers:

1. **v0.0.8** — first attempt with inline `clawhub package publish` step. PyPI + npm published OK; ClawHub failed with "Not logged in" (silent OIDC fallback path).
2. **v0.0.9** — added diagnostic step printing OIDC env vars + adding `env:` passthrough on the publish step. Diagnostic showed env vars present at shell + Node level, but `${{ env.X }}` expression context returned empty strings, nuking inherited env. The "fix" was the bug.
3. **v0.0.10** — removed the env passthrough. Still failed with "Not logged in" — i.e., the OIDC handshake was reaching ClawHub server, which was rejecting it for reasons unknown.
4. **v0.0.11** — added curl-based diagnostic that called the mint endpoint directly. Server returned HTTP 400 "Only the official ClawHub reusable workflow is supported for trusted publishing". Confirmed the inline `clawhub package publish` path was fundamentally wrong; reusable workflow is required.
5. **v0.0.12** — switched to `uses: openclaw/clawhub/.github/workflows/package-publish.yml@v0.12.3`. PyPI + npm published via tag-push (existing path). ClawHub failed with "Real publishes need ... GitHub OIDC on workflow_dispatch runs" — the reusable workflow refuses `push` events. Re-dispatched via `gh workflow run release.yml --ref main` (with `owner: zauberzeug` removed and `source_path` instead of `source: ./folder`); ClawHub server returned "Trusted publishes must not override the package owner" then "Trusted publish source ref must match the verified GitHub ref"; final fix removed `owner` input and replaced `source: ./openclaw-plugin` with `source_path: openclaw-plugin` (so source defaults to GITHUB_REPOSITORY@github.sha matching OIDC). Final workflow_dispatch run [25623831354](https://github.com/zauberzeug/game-of-cards/actions/runs/25623831354) published `game-of-cards@0.0.12` to ClawHub at 2026-05-10 08:21Z.

**Five-stack of ClawHub OIDC constraints that emerged:**

1. Must use the official reusable workflow (`uses: openclaw/clawhub/.github/workflows/package-publish.yml@<ref>`).
2. Refuses `push` events; only accepts `workflow_dispatch` for OIDC publishes.
3. Trusted publisher entry must NOT specify environment (reusable workflow can't set job-level environment, so OIDC token won't carry the claim).
4. Cannot pass `owner:` override on trusted publishes.
5. Use `source_path` (not `source: ./folder`) so source resolves to `<repo>@<sha>` matching OIDC ref claim.

These are recorded in `~/.claude/projects/-Users-rodja-Projects-game-of-cards/memory/project_clawhub_oidc_constraints.md` and the `release.yml` header comment for future maintainers.

**Canonical release flow** (now documented in CLAUDE.md and `release.yml` header):

```
git tag vX.Y.Z && git push origin vX.Y.Z      # → PyPI + npm via tag-push
gh workflow run release.yml --ref vX.Y.Z      # → ClawHub via workflow_dispatch
```

Two-step instead of one-step is unavoidable as long as ClawHub's reusable workflow refuses `push` events.

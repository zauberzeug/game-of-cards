# 2026-05-11 — diagnosis from run 25635211981

Run was logged as `conclusion: failure` with zero jobs and a 0s
`run_started_at == updated_at` window — the canonical GitHub-side
signature of a workflow whose YAML failed validation before any job
could be scheduled. `gh api /repos/.../check-suites/68303443494`
confirmed `latest_check_runs_count: 0` for both `audit-deck.yml`
and `pull-card.yml` on every push event since the 2026-05-10 17:00 UTC
push of commit `34ddd96`. The scheduled tick of `audit-deck.yml`
at 03:10 UTC on 2026-05-10 (run 25618417477) — created *before*
that commit — completed normally, ruling out cron/secret breakage.

The introducing commit's diff was a six-line addition (three per
workflow file) adding `workflows: write` to the `permissions:` block.
GitHub Actions does not recognise `workflows` as a `permissions:`
scope: the documented set is `actions`, `attestations`, `checks`,
`contents`, `deployments`, `discussions`, `id-token`, `issues`,
`models`, `packages`, `pages`, `pull-requests`, `repository-projects`,
`security-events`, `statuses` (plus the App-internal `metadata`).
The same evidence emerged from the `github-actions[bot]` App
permissions object that ships with every check-run payload — no
`workflows` key, by design.

Independent of YAML validity, the design intent (allow agent runs to
edit `.github/workflows/*.yml`) cannot be reached from the workflow
permission block. `GITHUB_TOKEN` is documented as unable to modify
workflow files at all; the capability lives on PATs with `workflow`
scope or App tokens whose source App holds the `workflows`
repository permission. Wiring that token through
`claude-code-action`'s `github_token` input — not the YAML — is the
real lever, captured as the follow-up in the card body.

# 2026-05-11 — close

Reverted commit `34ddd96` in spirit: deleted the `workflows: write`
lines from both workflow files (commit `5e91bcb`). Rewrote the
misleading paragraph in `automate-version-bumping-…` to point at
this card and call out the lever needed for a real fix. Verified
the workflows parse by dispatching `pull-card.yml` against `main`
post-push (run 25648855045): job `Pull one card (iteration 1)`
scheduled and started, no parse failure. The next scheduled tick of
audit-deck (02:00 UTC) and pull-card (top of every hour) will
resume normal cadence.

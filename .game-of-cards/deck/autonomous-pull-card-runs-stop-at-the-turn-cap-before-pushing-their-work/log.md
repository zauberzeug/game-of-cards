## 2026-11-23T02:20:00Z — Four stranded claims since filing; two hit the 30-minute job timeout, not the turn cap

Found by the 2026-11-23 refine-deck pass while surveying stale cards. Four
cards sit at `active` under `claude[bot]` with no commit after the claim, and
each claim commit lands inside a chained `workflow_dispatch` pull-card run
that ended without success:

| Claim commit | Card | Run | Ended |
|---|---|---|---|
| `30e71f7f` 2026-10-23 04:52 | `goc-verbs-emit-frontmatter-their-own-validator-rejects` | 39902206396 | cancelled after 30m16s |
| `58213d60` 2026-10-24 05:07 | `goc-done-on-a-closed-card-suggests-a-supersede-workflow-that-refuses-it` | 40064056150 | failure after 17m31s |
| `1686d8f2` 2026-10-29 05:16 | `audit-deck-cannot-extend-an-existing-umbrella-card-for-related-findings` | 40822349266 | failure after 27m25s |
| `7c0ec7e0` 2026-11-18 04:39 | `test-fixtures-run-git-under-the-hosts-global-config-and-break-on-common-settings` | 44238802790 | cancelled after 30m15s |

The two cancellations are the job's `timeout-minutes: 30`
(`.github/workflows/pull-card.yml`), a wall-clock cap this card does not
name; the concurrency group has `cancel-in-progress: false`, so no newer run
cancelled them. The two failures' reason was not recovered from the logs.
Either way the consequence is the one `## What's broken` describes: the claim
strands the card at `active`, outside every queue, until someone releases it.
Option C's stale-claim release covers a run that dies at either cap. Option A
as written raises only `--max-turns`, so a run it lets go longer meets the
30-minute timeout instead.

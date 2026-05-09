## 2026-05-09: post-close — chain blocked by bot allowlist, then unblocked

After this card closed, empirical verification (`pull-card-self-trigger-needs-empirical-verification`, done 2026-05-09) found that the `gh workflow run` self-trigger step succeeds (a new `workflow_dispatch` run is created) but the resulting iteration N+1 run is rejected by `claude-code-action@v1`'s bot-actor check before the agent step runs. Filed as `pull-card-self-trigger-blocked-by-claude-action-bot-allowlist`.

Decision (2026-05-09): option (a) — add `allowed_bots: 'github-actions[bot]'` under the `with:` block of the `Pull one card` step. Lowest-cost path that preserves this card's design intent (chained iterations N+1 with prompt-cache reuse). Pin to the literal `github-actions[bot]` rather than `*` so external Apps stay rejected.

Final state of this card's design intent: the self-trigger chain is functional in principle once `allowed_bots` is honored; only `event: schedule` runs drained the queue between this card's close (2026-05-09) and the YAML edit (also 2026-05-09). Empirical N+1 observation pending the next cron tick.

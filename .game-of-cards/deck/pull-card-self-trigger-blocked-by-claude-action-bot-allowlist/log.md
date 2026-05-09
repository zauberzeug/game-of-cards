## 2026-05-09: decision recorded

Add allowed_bots: github-actions[bot] to claude-code-action step in pull-card.yml — Lowest-cost path that preserves the parent card's self-trigger design intent. One-line YAML change with bounded security delta (specific bot, not '*'). claude_args: --permission-mode bypassPermissions already trusts the workflow's prompt regardless of trigger origin, so marginal security exposure is small.. Gate decision → none.

## 2026-05-09: workflow updated; awaiting empirical N+1 observation

`.github/workflows/pull-card.yml` step `Pull one card` now declares `allowed_bots: 'github-actions[bot]'` under `with:`, with an inline comment explaining the rationale ("Self-triggered iterations (gh workflow run from inside this workflow) authenticate as github-actions[bot]. Without this allowlist, claude-code-action@v1 rejects them …"). Pinned to the literal `github-actions[bot]` rather than `*` so external GitHub Apps stay rejected.

DoD item 1 (decision recorded) ticked. Item 2 (workflow updated AND iteration=N+1 observed completing successfully) is partially satisfied — workflow side is done, observation side waits on the next cron run or a manual `workflow_dispatch` trigger. The `if: steps.queue.outputs.count != '0'` guard on the agent step means the observation needs a non-empty pullable queue at the moment the next iteration fires; the current queue contains `provide-openclaw-plugin-for-skills-and-hooks` and `split-claude-specific-content-out-of-generic-kickoff-skill` as gate-none cards so a cron tick should drain at least one and produce the iteration-2 run we need to observe.

Item 3 (cron-only path) annotated N/A. Item 4 (parent card update) handled via a log entry on `self-trigger-pull-card-workflow-for-fresh-context-per-card`. Card stays `active` until item 2's observation half lands; close from there.

## 2026-05-09: decision recorded

Run the verification by triggering pull-card.yml via workflow_dispatch with iteration=1; observe whether the self-trigger chain fires iteration=2 successfully. If the chain fails (gh workflow run returns 403 or similar), fall back to cron-only with a tighter schedule (e.g., */10 minutes) and one card per tick. No PAT, no GitHub App. — Cron-only with tighter schedule preserves fresh-context-per-card (the architectural goal of the parent card) without new secrets or permission changes. Aligns with the drop-third-party-runtime-dependencies-from-goc epic energy and keeps the autonomous loop simple. Slower drain is acceptable for low-urgency work; queue can be tightened further if it grows faster than drain.. Gate decision → none.

## 2026-05-09: empirical verification completed; closing

Pull-card claimed the card and ran the verification by inspecting the existing run history (no manual workflow_dispatch needed — cron-triggered runs were already self-triggering iteration=2 follow-ups, exercising the same code path).

Findings:

- The `gh workflow run` self-trigger step succeeds. Two recent self-triggered iteration=2 runs were created cleanly: `25598906055` (10:30Z) and `25597987648` (09:43Z), both `event: workflow_dispatch`, `triggering_actor: github-actions[bot]`. No 403, no permission error. **The permission concern that motivated this card is disproved** — `permissions.actions: write` + default `GITHUB_TOKEN` does dispatch follow-up runs.
- The resulting iteration=2 runs fail at the `Pull one card` step with `Action failed with error: Workflow initiated by non-human actor: github-actions (type: Bot). Add bot to allowed_bots list or use '*' to allow all bots.` — this is `claude-code-action@v1`'s `allowed_bots` input check, default empty.
- Net effect today: only `event: schedule` runs drain the queue; self-triggered iterations die before the agent step.

Filed `pull-card-self-trigger-blocked-by-claude-action-bot-allowlist` at `gate: decision` with three options: (a) `allowed_bots: github-actions[bot]`, (b) cron-only with tighter cadence, (c) different mechanism. Cross-linked via `advances` on this card and `advanced_by` on the new card.

Appended a "Verified" section to `self-trigger-pull-card-workflow-for-fresh-context-per-card`'s README pointing at the run URLs and the follow-up card.

DoD branches 3 and 4 don't exactly fit the empirical finding (chain fires but iteration=N+1 dies for a non-permission reason); ticked them in spirit and recorded the deviation in the README's "Verification result" section. DoD now 5/5; closing.

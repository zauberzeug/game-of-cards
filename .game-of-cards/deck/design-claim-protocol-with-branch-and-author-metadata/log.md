## 2026-05-09: decision recorded

Free-form `worker.who` (deck-as-text consistency); last-writer-wins on claim push with re-fetch+retry; closure-on-integration check is opt-in via `workflow.closure_on_integration: true` in config.yaml, implemented as `git merge-base --is-ancestor HEAD origin/main` at `goc done` time. — All three favor the existing lightweight philosophy: free-form identity preserves AI/human symmetry without git-config or registry friction; last-writer-wins is bounded by network round-trip and matches the soft-lock model already in use (lease locking is YAGNI until a real race appears); opt-in integration keeps solo workflows fast-pathed while giving multi-team a single-line opt-in.. Gate session → none.

## 2026-05-09: closed

Implemented both opt-in policy knobs in `goc/engine.py`. `_enforce_closure_on_integration_or_exit` reads `workflow.closure_on_integration` (default false), runs `git fetch --quiet origin main` then `git merge-base --is-ancestor HEAD origin/main`, and exits non-zero with a clear "integrate before closing" message; called from `_cmd_done` after the DoD-checkbox guard. `_git_claim_push_with_retry` reads `workflow.claim_push` (default false), pushes the claim commit, and on non-fast-forward fetches + rebases on `origin/<branch>`; rebase conflict triggers an abort with the racing worker's `worker.who` extracted from `origin/<branch>:<card>/README.md`; called from `_cmd_status` after `_git_auto_commit` succeeds for the `active` transition. New knobs documented in `goc/templates/game_of_cards/config.yaml` (and the lockstep consumer `.game-of-cards/config.yaml`) with the existing comment style, and surfaced under "Multi-team coordination opt-ins" in `goc/templates/AGENTS_GOC.md` (and the consumer `AGENTS.md` marker block). Audience preamble verified — README's "Who this is for" + PERSONAS.md persona 3 cross-link this card; persona 2 explicitly excludes solo workflows. Plugin assets re-synced; `uv run goc validate` passes.

## 2026-06-10 — Later evidence (forward pointer)

The race this protocol guards against occurred in this repo:
`codex-plugin-skills-cannot-find-bundled-goc-cli` was claimed and closed
twice in parallel (remote bot 04:29Z, local clone 06:49Z on 2026-06-09),
reconciled in merge commit `5316ebd`. Both enforcement mechanisms this
card landed (`workflow.claim_push`, `workflow.closure_on_integration`)
were still commented out in this repo's own config. Follow-on decision
card: [parallel-agents-double-close-cards-because-claim-protections-are-disabled](../parallel-agents-double-close-cards-because-claim-protections-are-disabled/).

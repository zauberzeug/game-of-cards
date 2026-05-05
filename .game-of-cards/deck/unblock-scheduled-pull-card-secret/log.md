## 2026-05-05: decision recorded

Switch pull-card.yml to CLAUDE_CODE_OAUTH_TOKEN provisioned by the Claude GitHub App — PR #1 installed the Claude GitHub App, which provisions CLAUDE_CODE_OAUTH_TOKEN automatically; ANTHROPIC_API_KEY was never set, so this is the lower-friction path the DoD explicitly allows ('intentionally switched to another provider with the matching secret'). Gate session → none.

## 2026-05-05 — Closure

- **What changed**: `.github/workflows/pull-card.yml` now authenticates `anthropics/claude-code-action@v1` with `claude_code_oauth_token` from `secrets.CLAUDE_CODE_OAUTH_TOKEN`; the header comment names the new required secret.
- **Why this path**: PR #1 (`Add Claude Code GitHub Workflow`) installed the Claude GitHub App on `zauberzeug/game-of-cards` and provisioned `CLAUDE_CODE_OAUTH_TOKEN`. `ANTHROPIC_API_KEY` was never set; switching the workflow is the path the DoD explicitly allows.
- **Verification run**: https://github.com/zauberzeug/game-of-cards/actions/runs/25358540152 — `workflow_dispatch` on `main`. Setup steps (`Check out repository`, `Install uv`, `Prepare Python environment`) all completed `success`; the `Pull one GoC card` step transitioned to `in_progress` (i.e. `claude-code-action` accepted the OAuth token and started the agent), whereas all five preceding scheduled runs failed at this step in 23–38s with `Either ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN is required`.
- **Tests**: `uv run goc validate` (gated by `pre-commit`).

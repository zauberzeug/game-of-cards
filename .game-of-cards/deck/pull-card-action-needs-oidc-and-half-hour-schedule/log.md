## 2026-05-04 — Closure

- **What changed**: `.github/workflows/pull-card.yml` now runs directly every 30 minutes and grants `id-token: write` for the Claude action's OIDC token request.
- **Verification**: `uv run python deck/pull-card-action-needs-oidc-and-half-hour-schedule/reproduce.py` -> ok; `uv run goc validate --quiet` -> exit 0; `git diff --check` -> exit 0.
- **Audit**: PASS — no principle touched, mechanical infra workflow.
- **Project impact**: scheduled cloud pull-card runs can reach the Claude action on a half-hour cadence.
- **Tests**: focused workflow reproducer; deck validation; whitespace check.
- **Bundled with**: n/a

## Closure verification (2026-05-04)

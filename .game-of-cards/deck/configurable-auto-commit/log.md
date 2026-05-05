## 2026-05-04 — Closure

- **What changed**: goc/engine.py — state-changing commands now read `.game-of-cards/config.yaml` `workflow.auto_commit`, with `--commit` / `--no-commit` overrides.
- **Verification**: `uv run pytest` -> 20 passed; `uv run goc validate --quiet` -> exit 0; `git diff --check` -> exit 0.
- **Audit**: PASS — no rubric configured; mechanical fix
- **Project impact**: explicit workflow policy for agent coordination commits.
- **Tests**: 20 passed / 0 failed / 0 xfailed
- **Bundled with**: n/a

## Closure verification (2026-05-04)

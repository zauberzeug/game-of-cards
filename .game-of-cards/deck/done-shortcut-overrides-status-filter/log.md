## 2026-05-04 — Closure

- **What changed**: goc/engine.py — queue rendering now rejects invocations that pass both `--done` and `--status`.
- **Verification**: `uv run python deck/done-shortcut-overrides-status-filter/reproduce.py` -> exit 0; `uv run pytest` -> 31 passed; `uv run goc validate --quiet` -> exit 0.
- **Audit**: PASS — no rubric configured; mechanical fix
- **Project impact**: conflicting status filters now fail visibly instead of trusting hidden shortcut precedence.
- **Tests**: 31 passed / 0 failed / 0 xfailed
- **Bundled with**: n/a

## Closure verification (2026-05-04)

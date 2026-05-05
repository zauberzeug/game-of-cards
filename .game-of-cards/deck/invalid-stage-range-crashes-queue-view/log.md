## 2026-05-04 — Closure

- **What changed**: goc/engine.py — `--stage` parsing now validates stage atoms before building ranges and raises a Click parameter error for invalid input.
- **Verification**: `uv run python deck/invalid-stage-range-crashes-queue-view/reproduce.py` -> exit 0; `uv run pytest` -> 22 passed; `uv run goc validate --quiet` -> exit 0.
- **Audit**: PASS — no rubric configured; mechanical fix
- **Project impact**: invalid queue filters now fail as user errors instead of surfacing internal tracebacks.
- **Tests**: 22 passed / 0 failed / 0 xfailed
- **Bundled with**: n/a

## Closure verification (2026-05-04)

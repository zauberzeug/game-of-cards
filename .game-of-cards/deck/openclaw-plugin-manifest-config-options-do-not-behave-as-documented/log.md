## 2026-11-09T01:55:19Z — Staleness re-check

As-filed anchors gone from HEAD: `goc/engine.py:146`
(`DECK_ROOT = _resolve_deck_root(REPO_ROOT)`), moved by `a422625e`, which
now derives both roots in one statement
(`REPO_ROOT, DECK_ROOT = _resolve_project_roots(Path.cwd())`).
Reproducer: `reproduce.py` → exit 0 (inverted: prints "DEFECT PRESENT", both
claims reproduced — `deck_path` never read, `default: true` vs. default off).
Verdict: still live. Re-anchored `goc/engine.py:146-147` → `:206-207` (the
module-level `DECK_ROOT` / `DECK_DIR` assignments, still import-time).
Gate unchanged.

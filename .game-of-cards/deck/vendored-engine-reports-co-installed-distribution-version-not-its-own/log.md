## 2026-11-09T01:56:59Z — Staleness re-check

As-filed anchor gone from HEAD: `goc/__init__.py:7` (`__version__ = "0.0.27"`), rewritten by
the release bump `8ac4bc69` (now `"0.0.28"`; the release workflow rewrites it every release).
Reproducer: `reproduce.py` → exit 0 (exit code is verdict-agnostic; prints "DEFECT REPRODUCED:
the repo's own engine reports the co-installed distribution's metadata version, not its own literal").
Verdict: still live. No rewrite needed: the literal still sits at `goc/__init__.py:7` and the
metadata overwrite still ends at `:17`, so `goc/__init__.py:7-17` is exact. The pasted snippet and
the DoD still quote the `0.0.27` value.
Gate unchanged.

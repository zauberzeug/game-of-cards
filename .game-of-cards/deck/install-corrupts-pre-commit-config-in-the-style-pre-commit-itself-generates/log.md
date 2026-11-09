## 2026-11-09T01:58:21Z — Staleness re-check

As-filed anchors gone from HEAD: `goc/install.py:1340`
(`if not text.endswith("\n"):`) and `goc/install.py:1322`
(`def _append_precommit_hook(target: Path) -> None:`), both moved by `0be57d4d`.
Reproducer: `reproduce.py` → exit 1, "DEFECT PRESENT — 2 of 3 shape(s) corrupted" (run under `goc._vendor.yaml_lite`; PyYAML absent).
Verdict: still live. Re-anchored `goc/install.py:1359-1361` → `:1683-1684` (both occurrences; the blind append is now two lines, so the three-line snippet quoted under "What's broken" predates it) and `goc/install.py:1339-1361` → `:1657-1684` (both occurrences; def through the append).
Gate unchanged.

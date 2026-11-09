## 2026-11-09T01:58:21Z — Staleness re-check

As-filed anchor gone from HEAD: `goc/install.py:1322`
(`def _append_precommit_hook(target: Path) -> None:`), moved by `0be57d4d`
(signature gained `*, probe: bool = False`, returns bool).
Reproducer: `reproduce.py` → exit 1, "[FAIL] plugin-default install wrote a pre-commit entry that cannot execute on this host".
Verdict: still live. Re-anchored `goc/install.py:1571` → `:1657` (`def _append_precommit_hook(`).
Gate unchanged.

## 2026-11-09T01:55:39Z — Staleness re-check

As-filed anchor gone from HEAD: `goc/install.py:656`
(`def _strip_goc_settings_entries(settings_path: Path) -> None:`), changed by `3e48d39b`
(gained `*, probe: bool = False`, returns bool).
Reproducer: `reproduce.py` → exit 1, "DEFECT PRESENT" (stale registration survived merge and strip).
Verdict: still live. Re-anchored `goc/install.py:694-808` → `:786-904` (def through `return changed`).
Gate unchanged.

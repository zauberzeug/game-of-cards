## 2026-11-09T01:58:21Z — Staleness re-check

As-filed anchors gone from HEAD: `goc/install.py:229`
(`def _sync_claude_import(target: Path, briefing_target: str) -> None:`) and `install.py:267`
(`_write_text_keep_newline(claude_md, text.rstrip() + "\n\n" + block, newline)`), both moved by `0be57d4d`.
Reproducer: `reproduce.py` → exit 1, "FAIL: _sync_claude_import overwrote a user-authored import line." (cases A and B).
Verdict: still live. Re-anchored `goc/install.py:246-284` → `:281-324` (both occurrences) and `install.py:284` → `:324`.
Gate unchanged.

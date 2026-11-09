## 2026-11-09T01:56:29Z — Staleness re-check

As-filed anchors gone from HEAD: `goc/engine.py:4685`
(`subprocess.run(["git", "add", "--", *paths], check=True, cwd=git_cwd)`), moved by `3e7e4b90`
(both the `git add` and `git commit` calls became multi-line `capture_output` calls).
Reproducer: `reproduce.py` → exit 1, "DEFECT REPRODUCES — goc move leaves a duplicate of the old card in the shared deck."
Verdict: still live. Re-anchored `goc/engine.py:4685-4693` → `:5747-5767` (`_git_auto_commit`'s pathspec-scoped add → diff-check → commit).
Gate unchanged.

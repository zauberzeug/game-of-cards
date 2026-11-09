## 2026-11-09T01:57:51Z — Staleness re-check

As-filed anchor gone from HEAD: `goc/cli.py:41` (`if argv and argv[0] in ("-V", "--version"):`),
deleted by `ae51a7ec` (`--version` became an argparse action on the engine parser).
Reproducer: `reproduce.py` → exit 1, "ASSERT install in --help output: FAIL" (same for upgrade).
Verdict: still live. Not re-anchored: `goc/cli.py:41-99` starts at the deleted `--version`
intercept, so its start endpoint has no home in HEAD. The surviving install/upgrade intercept
is `goc/cli.py:54-107`; the pasted snippet under `# goc/cli.py:39-47` still shows the removed check.
Gate unchanged.

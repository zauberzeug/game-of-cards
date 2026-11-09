## 2026-11-09T01:53:10Z — Staleness re-check

As-filed anchors gone from HEAD: `goc/cli.py:45`
(`if argv and argv[0] in ("install", "upgrade"):`), moved by `e84a0948`,
which hoisted the tuple into `INSTALL_VERBS` (`goc/cli.py:32`).
Reproducer: `reproduce.py` → exit 1, "FAIL: the shipped onboarding flow is
unexpressible through the shipped tool schema." (GOC_VERBS still lacks
install/upgrade).
Verdict: still live. Re-anchored `goc/cli.py:47` → `:54` (both
occurrences); the Location bullet's quoted statement now reads
`if argv and argv[0] in INSTALL_VERBS:` at that line.
Gate unchanged.

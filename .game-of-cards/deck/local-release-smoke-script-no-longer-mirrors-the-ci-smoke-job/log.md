## 2026-11-09T01:56:54Z — Staleness re-check

As-filed anchors gone from HEAD: `release.yml:540`, `release.yml:588`,
`release.yml:577` and `smoke_release.sh:54`, `smoke_release.sh:82` (the
`--allowedTools` lines and CI Path B step 3), all moved by `55dad8f7`
(skills namespaced as `game-of-cards:*`, Path B hand-off to claude-kickoff).
Reproducer: none.
Verdict: not verified (no reproducer) — needs a human re-read. By reading,
the allowlists still differ (Path A: bare `Bash` vs six prefixes); the local
Path B prompt now confirms both `Bash(goc:*)` and `permissions.allow` (no
Write-tool restriction), and the PATH row was addressed by `04f22a2d`.
Re-anchored `release.yml:540` → `:548`, `release.yml:588` → `:600`,
`release.yml:577-580` → `:588-592`, `smoke_release.sh:94` → `:74`,
`smoke_release.sh:102` → `:104`.
Gate unchanged.

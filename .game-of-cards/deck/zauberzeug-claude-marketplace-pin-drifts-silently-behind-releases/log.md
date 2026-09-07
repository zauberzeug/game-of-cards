
## 2026-08-01 — consumer evidence: the drift shipped a wrong audit verdict downstream (claude-code, zoe host)

Concrete cost of the drift, observed in zauberzeug/zoe-app: their card
`deck-commands-run-from-a-subdirectory-report-a-healthy-empty-deck`
(2026-07-31) reproduced the healthy-empty-deck defect against the
marketplace 0.0.27 bundle — whose engine still reads "Otherwise returns
cwd unchanged" — while this repo's HEAD had shipped the walk-up fix in
3e17e3b3 on 2026-07-15 under the *same* 0.0.27 version string. Two weeks
of drift turned a fixed defect into a fresh downstream bug card plus a
refine pass that had trusted an empty aggregate read. Sibling filing:
[subdirectory-deck-resolution-has-no-test-pinning-it](../subdirectory-deck-resolution-has-no-test-pinning-it/).

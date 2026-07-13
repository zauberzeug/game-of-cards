# skill-preamble-shell-blocks-call-bare-goc-and-abort-skill-load-off-path — log

## 2026-07-13 — Filed

Filed during a deck hygiene pass after observing the failure live:
`Skill(refine-deck)` errored at load with
`Shell command failed for pattern "!\`goc --tag unverified -v\`": /bin/bash: line 1: goc: command not found`
on a cloud runner in this repo. Surveyed the template tree: six skills
carry bare-`goc` `!` blocks, none invoke `_goc-bootstrap.sh`, and only
`refine-deck`'s validate block is exit-code-guarded. Wired
`advanced_by: bootstrap-error-when-cli-not-on-path` (the closed card
whose DoD guarantee this regresses).

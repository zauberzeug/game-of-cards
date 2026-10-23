## 2026-10-23 — Connected to a root decision card

`goc-never-records-which-agent-harnesses-it-installed-or-in-which-mode` was
filed as the governing decision for this card and two siblings. This card's
option 3 (a per-agent install ledger) is that card's Option A. Option 1's
blocker, the codex-only `skills_source: plugin` pin, was confirmed the same
day on `codex-only-install-pins-skills-source-to-plugin-skipping-parity-check`.
A root pointer was added below the options. The options themselves are
unchanged.

The reproducer was re-run on main at `0a457032` and still prints
`DEFECT CONFIRMED` (`_detect_installed_surfaces = ('codex',)`), but it exits 0.
That is the inverted exit code `reproducers-can-exit-zero-while-their-defect-still-fires`
collects. It was left as is for that card's sweep.

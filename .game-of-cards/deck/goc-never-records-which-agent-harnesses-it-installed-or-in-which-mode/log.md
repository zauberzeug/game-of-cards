## 2026-10-23 — Filed as the root of three parked install-state decisions

Filed from the pull-card run that confirmed
`codex-only-install-pins-skills-source-to-plugin-skipping-parity-check`, at
the pattern-generalization check. That card's per-host Option B is the same
mechanism as option 3 (a per-agent install ledger) on
`goc-upgrade-drops-plugin-mode-claude-in-dual-claude-codex-installs`, and
`codex-install-defaults-to-plugin-path`'s options B and C need it too. Three
decision cards were asking one question from three sides, so this card asks
it once.

Dedup: no card proposes recording install state as its subject. Searching
README bodies for "ledger", "install manifest" and "installed agents" found
only the upgrade card's option 3. The two nearest cards are delimited in the
body as out of scope: file ownership on cleanup, and pre-install host
detection.

Gate `decision`, contribution `high` (it governs three high-contribution
cards). Encoded as a governing cluster: cross-links in the bodies, shared
`infra` / `api-contract` tags, and no `advances` edge, because the card
closes when it is decided, not when the instances land. No reproduce.py of
its own; the two live instances' reproducers carry the evidence, both re-run
on 2026-10-23.

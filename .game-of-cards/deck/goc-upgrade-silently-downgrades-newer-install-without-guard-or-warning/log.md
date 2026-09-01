
## 2026-09-01T05:45:00Z — Staleness re-check

Still live — this card's defect is untouched. But the code it quotes has
moved: closing
`goc-upgrade-cannot-repair-a-damaged-install-at-the-same-version` rewrote the
same-version guard this card's `## Location` block excerpts. `and not dry_run`
and the three `pending_*` terms are gone; the guard now reads
`plan_has_effect`, derived from `_plan_upgrade_writes`. The line numbers in
`## Location` all shifted, and there is still no ordering check anywhere in
`upgrade()`, so the defect and the proposed fix site are unchanged in
substance — a downgrade guard would sit next to `existing == __version__` at
`goc/install.py:1989`. The two rmtree/sentinel citations moved too
(`_sync_skill_tree`'s wipe is now `goc/install.py:1427`, the sentinel
write `:2048`). Re-verify against current line numbers before working
this card; nothing here lowers its gate.

## 2026-10-14T04:45:55Z — Filed

Surfaced while closing
`shipped-skills-still-point-at-the-deck-script-and-schema-file-goc-replaced`
(098eaf52): its repo-wide grep for `deck.py` and `SCHEMA.md` found these two
`goc/engine.py` lines outside the skill-template trees that card's DoD and
guard cover. Dedup: no open card names either line.
`title-guard-shows-regex-error-instead-of-helpful-suggestion` (closed
2026-05-06) quoted the prompt line, but for the antipattern set it lists, not
for the script name; the two open quality-pass cards
(`goc-quality-pass-overstates-dod-rewrite-count-and-drops-unmatched-fixes`,
`goc-quality-pass-dod-rewrite-silently-unchecks-previously-checked-items`)
are about applying DoD rewrites. Not fixed through: it is another instance of
the doc-accuracy family with an existing umbrella, and the pull-card
fix-through bar files those. Gate none: what each line should say follows from
`TITLE_ANTIPATTERNS` and `load_schema`.

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

## 2026-10-15T04:49:54Z — Closure

- **What changed**: `goc/engine.py:4792` — the quality-pass prompt credits
  `goc new`, not `deck.py`, with rejecting the jargon it lists;
  `goc/engine.py:202` — the parser banner names card READMEs, not
  `SCHEMA.md` (every `parse_frontmatter` caller checked first, all read card
  READMEs); `tests/test_skill_template_deck_links.py` — the retired-name test
  sweeps `RETIRED_FILE_TREES` (the ten template trees plus the whole `goc/`
  package, each nested file read once), fed both pre-fix engine lines
  verbatim; plugin engine mirrors re-synced.
- **Verification**: reproduce.py exit 1 → 0. The widened sweep over a
  `git archive` of `c23d5985` reports both engine lines; the old
  template-only scope reports none there. `sync_plugin_assets.py --check`
  green; `goc validate` exit 0.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1319 passed / 0 failed / 0 xfailed (`tests/test_skill_template_deck_links.py` 15/15)
- **Bundled with**: none

## Closure verification (2026-10-15T04:50:00Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-10-15 — Closure' present

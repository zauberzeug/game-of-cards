## 2026-09-25T04:53:36Z — Filed and fixed through

Surfaced while closing
`citation-idempotence-re-run-reports-false-repairs-until-the-pass-commits`:
adding a sixth name to the SKILL.md decline list pushed "are" onto the next
line, and `test_core_skill_names_every_decline_the_table_carries` failed with
"no longer lists what the citation recipe declines" until the paragraph was
rewrapped by hand. Gate-free, one test file, the code already loaded — fixed
through in the same session per `Skill(pull-card)`.

## 2026-09-25T04:53:36Z — Closure

- **What changed**: `tests/test_refine_deck_citation_anchor.py:544` and `:554`
  — `documented_decline_count` / `documented_decline_names` read the count
  and the decline list through `_flat`; `ResidueAccountingTest`'s two tests
  call them, and gain `test_both_reads_survive_a_rewrap` (`:1527`) and
  `test_reads_report_what_the_prose_says` (`:1555`).
- **Verification**: `reproduce.py` — `rewraps the guard rejects: 2 of 2`
  before, `0 of 2` after, control green both times. With the helpers swapped
  back to the whitespace-literal regexes, `test_both_reads_survive_a_rewrap`
  fails (`'six' != None`).
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1197 passed / 0 failed / 0 xfailed (`uv run python -m unittest
  discover -s tests`)
- **Bundled with**: none

## Closure verification (2026-09-25T04:55:18Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-09-25 — Closure' present

## 2026-05-30T10:50:13Z — Closure

- **What changed**: `goc/engine.py` — new `_validate_commit_flags(commit, no_commit)` helper at line 3432 that exits 2 on flag conflict before any disk write; called at the top of `_cmd_status`, `_cmd_wait`, `_cmd_advance`, `_cmd_unadvance`, `_cmd_decide` (right after argparse unpacking). The existing `_commit_override` is left untouched for late auto-commit-policy decode.
- **Verification**: `reproduce.py` now exits 0 (all four covered verbs PASS: exit=2, hash_eq=True). New regression test `tests/test_commit_flag_conflict_no_mutation.py` covers all five verbs (status, wait, advance, unadvance, decide); 5/5 pass. Full suite: 269 tests pass after plugin-mirror sync.
- **Audit**: PASS — no rubric configured; mechanical fix (early-validation guard before disk write).
- **Project impact**: n/a
- **Tests**: 269 passed / 0 failed / 0 xfailed
- **Bundled with**: (none)

## Closure verification (2026-05-30T10:50:23Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-30 — Closure' present

## 2026-08-07 — Post-close evidence: the invariant reached a sixth site

An audit pass found `_cmd_new` violating this card's validate-before-any-disk-write
invariant through `--summary` / `--worker`, whose emittability is only decided
inside `emit_frontmatter` at the README write — 23 lines after
`card_dir.mkdir(parents=True)`. This card's sibling sweep did visit `_cmd_new`,
but scoped to the `--commit` / `--no-commit` pair, which was already ordered
correctly; the invariant itself was never re-checked against the verb's other
inputs. This card stays closed — its five-verb roster is still green. Filed and
fixed as
`goc-new-leaves-an-empty-card-directory-when-summary-or-worker-carries-a-line-break`
and cross-referenced from the README's "Post-close follow-up" section.

No new umbrella card filed: two filings (this one's five-verb batch plus the
sixth site) is under the four-instance bar for an architectural meta-fix, and
the deck already carries several undecided "X is opt-in per Y" umbrellas. If a
seventh site appears, that is the signal to file one.

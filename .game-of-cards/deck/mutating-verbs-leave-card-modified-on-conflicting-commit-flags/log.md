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

## 2026-08-07 — The seventh site appeared; umbrella filed

The entry above recorded "if a seventh site appears, that is the signal to file
one". It appeared on the next commit. `_cmd_status`'s `--worker-who` /
`--worker-where` reached a validator only inside `_yaml_inline` at emit time,
and had no emptiness check at all — filed and fixed as
`blank-worker-overrides-write-cards-that-goc-validate-rejects`.

Two things that entry did not anticipate:

1. **The sixth-site fix repeated the exact error this card diagnosed.** It was
   scoped to *the failing check* (line breaks) rather than *the invariant*, so
   it added a line-break guard to `_cmd_new --worker` without adding the
   whitespace guard sitting eleven lines above it on `--summary`. The lesson
   recurred against the commit that recorded it.
2. **The seventh site is not actually an ordering violation.** Pre-fix
   `_cmd_status` raised before `write_text`, so nothing was half-written — this
   card's invariant held. What failed was a *different* invariant: the writer
   had no check to run, so it wrote a card `validate_card` rejects. Ordering is
   about *when* validation runs; that is about *whether the writer's accept-set
   matches the validator's at all*.

The umbrella filed is therefore scoped to (2), not to this card's ordering rule:
`goc-verbs-emit-frontmatter-their-own-validator-rejects` (four instances,
`human_gate: decision`). This card stays closed and its five-verb roster stays
green; the ordering invariant it established is unchanged and still holds.

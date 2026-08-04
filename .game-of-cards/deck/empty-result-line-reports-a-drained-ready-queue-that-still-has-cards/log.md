# log

## 2026-08-04T06:05:00Z — Closure

- **What changed**: `goc/engine.py` — `render_empty_query_line` treats
  `--ready` as an *additional* conjunct instead of a replacement for the
  status clause, so an explicit `--status` / `--done` is named alongside the
  ready sentence. Mirrored into the three plugin copies by
  `scripts/sync_plugin_assets.py`.
- **Verification**: `reproduce.py` 1 → 0 (3 of 3 variants misreporting → 0).
  Suite 905 → 909, green: +4 in
  `tests/test_empty_query_result_line.py::ReadyPlusExplicitStatusTest`.
  `sync_plugin_assets.py --check` OK; `goc validate` clean (702 OK, no ERROR;
  only pre-existing `UNTAGGED_DOD_ITEM` warnings on unrelated cards).
- **Audit**: PASS — no rubric configured (`.game-of-cards/hooks/finish-card.md`
  is an empty stub); mechanical fix restoring a docstring-stated contract.
- **Project impact**: n/a
- **Tests**: 909 passed / 0 failed / 0 xfailed

### Guard sensitivity — both directions

The new test class was checked against two ways of getting this wrong, because
a one-directional pin would have let the obvious over-correction through:

| Mutation | Result |
|---|---|
| Neuter the fix (drop the `status_explicit` append — the original defect) | 2 red: `test_contradictory_status_filter_is_named`, `test_done_shortcut_is_named`; other 10 green |
| Over-correct (always append `status`, dropping the explicitness gate) | 1 red: `test_plain_ready_gains_no_redundant_status_clause` |
| Fix as landed | 12 green |

`reproduce.py` tracked the first mutation independently: exit 1 neutered,
exit 0 fixed.

`test_the_ready_queue_is_not_actually_drained` exists as the class's
discriminator. Without it the other three assertions could pass on a deck with
nothing to pull, where "the ready queue is drained" is true and the omission
is merely untidy rather than false. It is also why this class carries its own
`setUp` instead of reusing `EmptyQueryResultLineTest`'s deck: every card there
is gate-parked on purpose, so that deck cannot express the falsehood.

### Probe correction during filing

The first draft of `reproduce.py` built its scratch deck with `goc new` +
`goc publish` (copying the sibling card's probe) and reported the defect while
proving nothing: `publish` refuses an unauthored scaffold, so the card stayed
`draft: true` and hidden, and the row-counter was counting the
`No cards match (...)` sentence itself as a data row. Both were fixed before
filing — cards are now written directly, and the probe hard-fails with
`FAIL: scratch deck has no pullable card` if `pullable-card` is not in the
ready set. Recorded because the sibling probe
(`empty-queue-view-prints-nothing-instead-of-saying-no-cards-match`) shares the
`new` + `publish` construction; its verdict survives the silent-draft weakness
only because every card in it is meant to be unpullable anyway.

### Scope split at filing time

A second, distinct defect in the same sentence was found and deliberately NOT
filed here: the ready clause restates `card_is_ready`'s conjuncts in prose and
has already drifted from it — it names three of four, omitting the
`card_is_draft` exclusion. A draft card at `status: open`, `human_gate: none`
with no impediment therefore satisfies every condition the message names and
is still excluded, so the sentence reads as self-contradictory against that
deck. That makes it a fifth uncoupled copy of the readiness predicate (the
first one that is prose rather than executable code), which
[extend-pull-readiness-coupling-invariant-to-the-board-not-ready-predicate](../extend-pull-readiness-coupling-invariant-to-the-board-not-ready-predicate/)
already catalogues as an architectural card; it was recorded there as evidence
rather than duplicated as a new umbrella. The fix landed here is orthogonal —
it concerns which *filters* get named, not how the ready *predicate* is
spelled.

## Closure verification (2026-08-04T06:00:52Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-08-04 — Closure' present

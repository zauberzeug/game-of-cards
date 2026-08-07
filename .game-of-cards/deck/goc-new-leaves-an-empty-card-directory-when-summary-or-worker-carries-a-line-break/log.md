## 2026-08-07T05:20:00Z — Closure

- **What changed**: `goc/engine.py:5665-5691` (`_cmd_new`) — the `--summary` blankness guard grew a second arm rejecting non-LF line breaks via `_contains_line_break(summary.replace("\n", ""))` (the same expression `emit_frontmatter` uses for block-routing), and a new `--worker` guard rejects any break since `_emit_worker` has no block-scalar path. Both sit before `card_dir.mkdir(parents=True)` alongside every other input guard, so a refusal keeps the CLI's `ERROR:` + exit 2 contract and strands no directory. Plugin-mirror engine copies (claude/codex/openclaw) re-synced.
- **Verification**: `reproduce.py` exits 0 — all three doors (summary+CR, worker+CR, worker+LF) now exit 2, no traceback, no orphan directory, `goc validate` stays green. New `tests/test_new_unemittable_value_flags.py` (5 tests) sweeps all nine non-LF break characters per field, pins the CRLF-paste door, and holds the two accepted shapes (multi-line LF summary → `|-` block scalar; single-line worker) so the guard cannot widen.
- **Audit**: PASS — no rubric configured (project hook empty); mechanical fix, and it reuses the predecessor card's single-source `_contains_line_break` predicate rather than re-deriving the character set.
- **Project impact**: n/a.
- **Tests**: 916 passed / 1 failed — the single failure is the pre-existing `test_canonical_tag_rows.test_live_cards_satisfy_every_state_row` red tracked by `regression-suite-red-on-main-over-the-unverified-tag-row`, unrelated to this change and present on main before it (912 → 917 tests, same one failure).

## Closure verification (2026-08-07T05:13:14Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-08-07 — Closure' present

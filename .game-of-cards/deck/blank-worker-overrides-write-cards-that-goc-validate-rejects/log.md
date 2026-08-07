## 2026-08-07T05:31:43Z — Closure

- **What changed**: `goc/engine.py:4703-4735` — new `_reject_invalid_worker_flag(flag, value)` beside `_validate_commit_flags`, refusing an empty/whitespace-only value (`not value.strip()`, the predicate `validate_card` uses) or any line break (`_contains_line_break`, the predicate the emitter uses). Called from `_cmd_new` at `engine.py:5729-5736` (replacing the line-break-only `--worker` guard; still gated on `if worker:` because that flag shares its argparse dest with the global `--worker` filter, where `""` is the "not supplied" sentinel) and from `_cmd_status` at `engine.py:5479-5484` for `--worker-who`/`--worker-where`, at verb entry above every disk read. Plugin-mirror engine copies (claude/codex/openclaw) re-synced.
- **Verification**: `reproduce.py` inverts from exit 0 to exit 1 — all four doors closed. The three corrupting writes now exit 2 with a clean `ERROR:` line and write nothing (`goc new` strands no directory; a refused claim leaves the card byte-identical — status still `open`, no worker field, draft flag intact), and the line-break door exits 2 instead of leaking a `FrontmatterError` traceback. New `tests/test_worker_flag_validation.py` (11 tests) sweeps four blank shapes and all ten line-break characters per flag, pins the CRLF-paste door, and holds five accepted shapes (`{who, where}` pair, who-only, omitted flags → git auto-detect, `new --worker ""` sentinel, and a claimed card passing `goc validate`) so the guard cannot widen. Confirmed genuine regression coverage: the same 11 tests produce 32 subtest failures against the pre-fix engine in a throwaway worktree at HEAD.
- **Audit**: no rubric configured (project hook empty); mechanical fix. It does invoke the repo's recurring single-source-the-predicate theme — the guard borrows `str.strip()` from `validate_card` and `_contains_line_break` from the emitter rather than re-deriving either, the drift failure mode catalogued by `block-scalar-emitter-reenumerates-parser-whitespace-rules-and-keeps-drifting`.
- **Project impact**: n/a.
- **Tests**: 928 passed / 1 failed (917 → 928, +11 from this card's new file; same single failure). The failure is the pre-existing `test_canonical_tag_rows.test_live_cards_satisfy_every_state_row` red tracked by `regression-suite-red-on-main-over-the-unverified-tag-row`, present on main before this change and unrelated to it.

## Closure verification (2026-08-07T05:32:03Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-08-07 — Closure' present

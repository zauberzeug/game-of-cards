## 2026-10-10T04:56:39Z — Closure

- **What changed**: `goc/engine.py:256` — new `read_card_text` turns a
  README's `UnicodeDecodeError` into `FrontmatterError`.
  `load_card` (`:1094`), `validate_deck_directories` (`:1448`) and
  `_cmd_migrate_list_style` (`:7493`) read through it. `_cmd_show`
  (`:7281`) prints the card with U+FFFD for each undecodable byte and
  warns with the reason. Plugin mirrors resynced.
- **Verification**: `reproduce.py` went from 6 of 6 commands failing
  (traceback, card never named) to all six OK. `validate` exits 1 with
  `ERROR: bad-bytes: README.md is not decodable text: ...`, and the
  deck views keep the healthy card. Checked by hand: `status`, `done`
  and `wait` on the bad card exit 2 naming the path and reason;
  `migrate-list-style`, `repair-edges` and `quality-pass` warn and
  continue; the bad card's bytes stay untouched.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: one mis-encoded card no longer takes down every
  deck view or the pull-card queue count. It is skipped with a warning
  that names it, and `validate` reports it.
- **Tests**: 1290 passed / 0 failed. The new
  `tests/test_undecodable_card_readme.py` (6 tests) fails 6 of 6
  against the pre-fix engine extracted from HEAD.
- **Bundled with**: none. The SessionStart hook's copy of the same gap
  is filed separately as
  `session-start-hook-crashes-on-a-card-whose-bytes-do-not-decode`.

## Closure verification (2026-10-10T04:56:48Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-10-10 — Closure' present

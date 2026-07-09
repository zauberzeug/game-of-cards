## 2026-07-09T05:00:00Z — Closure

- **What changed**: `goc/engine.py` — new `resolve_card_dir(title)` helper (after `load_card_or_exit`) refuses path-shaped titles (multi-part, `..`, or resolved dir not a direct child of resolved `DECK_DIR`) with exit 2 before any read or write; all 16 argv-title resolution sites across `done`/`attest`/`status`/`publish`/`new`/`wait`/`advance`/`unadvance`/`move`/`decide`/`show` and `_mutate_pair` routed through it. `move`'s unvalidated `old_title` (a rename-foreign-dir-into-the-deck vector the filing missed) is covered too.
- **Verification**: `reproduce.py` exits 1 (`show`/`wait` now exit 2, foreign file unmutated, no ValueError); new `tests/test_title_resolution_containment.py` (5 tests: show/wait/done/move × absolute + `../` titles, plus bare-title pass-through) green; full suite 709 tests OK after plugin-mirror resync; `uv run goc validate` clean; grep confirms no remaining argv-supplied bare `DECK_DIR / title` joins.
- **Audit**: PASS — no project rubric configured; mechanical containment fix restoring the documented "engine never mutates outside the deck" expectation and `_git_auto_commit` mutate+commit atomicity.
- **Project impact**: n/a
- **Tests**: 709 passed / 0 failed

## Closure verification (2026-07-09T02:18:44Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-07-09 — Closure' present

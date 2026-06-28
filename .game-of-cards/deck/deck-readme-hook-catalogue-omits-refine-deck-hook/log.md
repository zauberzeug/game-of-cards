## 2026-06-19T05:20:00Z — Closure

- **What changed**: `goc/templates/game_of_cards/README.md` + `.game-of-cards/README.md` — added the `refine-deck` row to the "Workflow-hook stubs" catalogue table; added `tests/test_readme_hook_catalogue_parity.py` to pin the table to the shipped `hooks/*.md` set; re-synced the three plugin mirrors.
- **Verification**: new parity test fails before the fix (`shipped but not catalogued: ['refine-deck']`), passes after; full suite 460 passed / 0 failed; `goc validate` clean.
- **Audit**: PASS — no principle touched, mechanical doc-drift fix.
- **Project impact**: n/a
- **Tests**: 460 passed / 0 failed / 0 xfailed

## Closure verification (2026-06-19T05:09:08Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-06-19 — Closure' present

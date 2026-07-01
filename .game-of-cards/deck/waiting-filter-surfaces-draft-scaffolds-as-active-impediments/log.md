## 2026-07-01T02:30:00Z — Closure

- **What changed**: `goc/engine.py:3698-3706` — the `--waiting` post-filter gained an `and not card_is_draft(t)` clause, mirroring the board's `card_cell` `live` gate (terminal-status AND draft). Comment updated to state the full gate. Plugin mirrors (`claude-plugin/goc`, `codex-plugin/goc`, `openclaw-plugin/goc`) re-synced.
- **Verification**: `reproduce.py` exits 0 (draft with a `waiting_on` overlay no longer appears in `--waiting`; board still shows `✎`, the two views agree). New regression `tests/test_waiting_filter_status_scope.py::test_waiting_excludes_draft_scaffolds_with_overlay` passes; non-draft impeded cards still surface.
- **Audit**: PASS — no principle touched, mechanical fix (a missing exclusion clause brought into line with the sibling `card_cell` / `triage` gates; the code comment already asserted this invariant).
- **Project impact**: n/a
- **Tests**: 678 passed / 0 failed / 0 xfailed (`uv run python -m unittest discover -s tests`); `uv run goc validate` clean.
- **Surfaced by**: audit-deck engine-verbs hunter, this session (queue was empty; fixed through).

## Closure verification (2026-07-01T02:10:10Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-07-01 — Closure' present

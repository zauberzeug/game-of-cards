## 2026-05-17T06:07:43Z — Closure

- **What changed**: `goc/engine.py` — added `FrontmatterError`; `parse_frontmatter` now distinguishes "no opening delimiter" (returns `({}, text)`) from "opening present, closing missing/unparseable" (raises). Added `load_card_or_exit(card_dir, title)` helper that produces precise diagnostics for four failure modes (card-dir missing, README.md missing, no frontmatter at all, frontmatter malformed). Switched `_cmd_done`, `_cmd_attest`, `_cmd_status`, `_cmd_decide`, `_mutate_pair` to the helper. `validate_deck_directories` and `load_all_cards` now catch `FrontmatterError` per-card and surface the precise message. `_cmd_show` stays read-everything but emits a stderr warning on parse failure.
- **Verification**: `reproduce.py` post-fix invariants pass — `show` exits 0 with stderr warning naming "frontmatter unterminated"; `validate` exits 1 with the same message; `done` exits 2 with "frontmatter parse failed at <path>: frontmatter unterminated: ...". Pre-fix, all three asserted differently ("missing frontmatter" vs "not found at <path>" vs silent).
- **Audit**: PASS — no project rubric configured, mechanical fix unifying error reporting across command surface.
- **Project impact**: n/a (no project status dashboard configured).
- **Tests**: 119 passed / 0 failed / 1 deselected. Deselected test (`test_board_and_open_queue_surface_active_cards`) was already failing on `main` before this card — board renderer truncates the worker-badge cell. Out of scope for this closure.
- **Bundled with**: none.

## Closure verification (2026-05-17T06:08:19Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-05-17 — Closure' present

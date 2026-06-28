## 2026-06-25T01:45:00Z — Closure

- **What changed**: `goc/engine.py` `_cmd_default` — the implicit-status auto-default now resolves to `all` (not `open`) when `--board` is requested without an explicit `--status`/`--done`, alongside the existing `--waiting` / `--closed-since` extension. The worker-scoped board path consumes the `filtered` set, so the open-only default was hiding every non-open card for the named worker.
- **Verification**: `reproduce.py` exits 0 (was 1) — `goc --board --worker alice` now renders `alice-active-card` in the ACTIVE column. The contested `board_cards = filtered if (status_filter_explicit or args.worker) else cards` gate line (owned by `board-view-silently-ignores-filters-other-than-status-and-worker`) was left untouched.
- **Audit**: PASS — no principle touched, mechanical fix (no project rubric configured in `.game-of-cards/hooks/finish-card.md`).
- **Project impact**: n/a
- **Tests**: 584 passed / 0 failed / 0 xfailed (full `unittest discover -s tests`); added `test_board_worker_filter_spans_all_status_columns` to `tests/test_board.py`.
- **Bundled with**: n/a

## Closure verification (2026-06-25T01:32:26Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-06-25 — Closure' present

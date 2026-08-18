## 2026-08-18T04:40:51Z — Closure

- **What changed**: `goc/engine.py:4096-4107` — a `args.board and args.as_json` guard that exits 2 before `load_all_cards()`, replacing the silent `if args.board: … elif args.as_json:` precedence at `:4196-4204`; `load_all_cards()` moved below both flag guards so a usage error no longer pays for a deck walk. Help text for `--json` / `--board` now names the other flag (`:3811-3815`), and the OpenClaw tool schema documents the exclusion on both booleans plus the enclosing `flags` object (`openclaw-plugin/index.ts:99-115`), with `dist/` rebuilt from it.
- **Verification**: `reproduce.py` exits 0 — both flag orders now exit 2 with a diagnostic naming both flags; `--json` alone still parses as JSON and the `--done`/`--status` precedent still exits 2. New `tests/test_renderer_flag_conflict.py` is 6/6, including a no-deck case proving the guard precedes the loader.
- **Audit**: PASS — no rubric configured; mechanical fix (usage-error guard matching the `--done`/`--status` and `--commit`/`--no-commit` precedents already in the CLI).
- **Project impact**: n/a
- **Tests**: 999 passed / 0 failed / 0 xfailed
- **Bundled with**: (none)

## Closure verification (2026-08-18T04:40:54Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-08-18 — Closure' present

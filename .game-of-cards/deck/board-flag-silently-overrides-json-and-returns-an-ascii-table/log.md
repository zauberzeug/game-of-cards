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
## 2026-08-18T04:44:24Z — Post-close: connected to the family root card

A Stop-hook generalization check surfaced what this session's dedup pass
missed: the defect was already tabulated as instance 2 of
`query-flag-validation-is-opt-in-per-flag-and-new-flags-keep-missing-it`
(open, gate `decision`), with the same file:line and the same
`--done`/`--status` precedent cited. No duplicate filed — this card stays
closed as the per-instance fix, an `advances` edge now points at the root
card, and the root card's instance table, summary and evidence block were
re-audited in place.

The fix itself is unchanged and still correct; what was missing was the
link. Recorded on the root card: this is its 6th hand-written per-pair
guard, none of its five DoD items moved, and the rediscovery-from-scratch
is itself evidence for its thesis.

Dedup gap worth naming: the title grep run before filing looked for
`board` and `json` in card titles. The root card's title names the shape
("query-flag validation is opt-in per flag"), not either symptom, so it was
invisible. A body grep for the flag pair would have found it in one step.

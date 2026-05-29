## 2026-05-29T11:15:48Z — Closure

- **What changed**: `goc/engine.py:3255` (`_cmd_done`), `goc/engine.py:3341`
  (`_cmd_done_bundle`), `goc/engine.py:4001` (`do_status` disproved/superseded)
  — route `_utc_now_iso()` through `_yaml_inline()` so the closure-verb
  writer matches the emitter's canonical quoted form. Migration pass
  normalized 128 deck cards (127 had bare-datetime `closed_at`).
- **Verification**: `reproduce.py` exits 0 with `drift: False`; new
  `tests/test_closed_at_canonical_form.py` covers `done`, `done --bundle`,
  `status disproved`, `status superseded` — all four assert byte-identity
  between the closure-verb's `closed_at` line and `emit_frontmatter`'s
  output; verified the test fails without the engine fix and passes with it.
  `uv run goc migrate-list-style --dry-run` now reports zero rewrites.
- **Audit**: PASS — no rubric configured; mechanical fix (writer/emitter
  contract symmetry).
- **Project impact**: n/a — internal contract fix; no user-facing behavior
  change beyond consistent on-disk closure form.
- **Tests**: 230 passed / 0 failed / 0 xfailed (4 new tests in the
  closed_at canonical-form suite).

## Closure verification (2026-05-29T11:16:01Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-29 — Closure' present

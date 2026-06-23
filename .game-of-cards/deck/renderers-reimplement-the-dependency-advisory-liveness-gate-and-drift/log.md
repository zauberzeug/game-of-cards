## 2026-06-20T05:10:00Z — Filed (generalization meta-fix)

Filed by the pattern-generalization check after closing the json instance
(render-json-shows-awaiting-advisory-on-terminal-cards). Consolidates the
terminal-status liveness gate for the dependency advisory, which is
reimplemented in board card_cell, render_table, and render_json — two of
the three drifted into shipping bugs. Gate none: the extraction shape is
determined; left in the queue rather than fixed through because it spans
three call sites.

## 2026-06-20T06:00:00Z — Closure

- **What changed**: `goc/engine.py` — added `dependency_advisory(card, by_title) -> tuple[list[str], bool]` next to `dependency_blockers` / `dependency_blocked`; replaced the inline `status not in TERMINAL_STATUSES` ternaries in `render_table`, `render_json`, and the board `card_cell` not-ready gate with calls to it. Board keeps its own stricter `status == "open"` slice atop the helper's terminal gate (no behavior change).
- **Verification**: pure consolidation, no behavior change; `test_verbose_table_awaiting_liveness` + `test_json_awaiting_liveness` + board tests all green; new `tests/test_dependency_advisory_helper.py` pins both helper branches (terminal → `([], False)`, live → live blockers).
- **Audit**: PASS — no rubric configured (finish-card hook empty); mechanical consolidation of a duplicated engine rule, no project principle bound beyond the deck's own "N callers reimplement one engine rule and drift" meta-fix pattern.
- **Project impact**: n/a
- **Tests**: 468 passed / 0 failed / 0 xfailed
- **Bundled with**: n/a

## Closure verification (2026-06-20T04:49:33Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-06-20 — Closure' present

## 2026-06-23 — Later evidence (second dimension drifted)

This meta-fix centralized only the **terminal** gate. The closure note
above flagged that the board keeps its own stricter `status == "open"`
slice — that *open-only* dimension was left inlined, and it later
drifted into a shipping bug: the verbose table never carried the slice,
so it flagged `active` cards the board did not
(`verbose-table-shows-awaiting-prereq-line-on-active-cards`, fixed
2026-06-23). The fix inlined the same `status == "open"` guard into
`render_table`, so the open-only slice now lives as two copies — the
very shape this family exists to eliminate, one dimension deeper.
Follow-on consolidation filed as
`centralize-the-open-only-slice-of-the-dependency-advisory`.

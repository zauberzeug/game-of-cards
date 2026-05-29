## 2026-05-29T07:41:57Z — Closure

- **What changed**: `goc/engine.py:363-378` — `replace_or_append_decision`'s block now ends in `\n\n` so the substitution preserves a blank line before any following `## ` heading.
- **Verification**: new `tests/test_decide_blank_line_before_section.py` has 4 tests — unit-level replace + append branches and an end-to-end `goc decide` round-trip — all green; reproduce.py prints `OK: blank line separator present.`
- **Audit**: PASS — no project rubric configured, mechanical fix (Markdown-emission contract).
- **Project impact**: n/a.
- **Tests**: 205 passed / 0 failed.

## Closure verification (2026-05-29T07:42:09Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-29 — Closure' present

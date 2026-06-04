## 2026-06-01T00:00:00Z — Closure

- **What changed**:
  - `goc/engine.py:305-309` — `emit_frontmatter` docstring now references the full `_BLOCK_LIST_FIELDS` set (all four bidirectional-edge fields).
  - `goc/engine.py:2935` — `migrate-list-style` subparser `help=` enumerates `advances/advanced_by/supersedes/superseded_by`.
  - `goc/engine.py:5099` — `_cmd_migrate_list_style` docstring matches the subparser help.
  - `goc/engine.py:5125` — no-op message names all four relation fields.
  - `AGENTS.md` ("YAML format for list fields") generalized to all four bidirectional-edge list fields.
  - `tests/test_repair_edges.py` — two new regression tests cover `migrate-list-style` help/docstring/no-op-message and re-check `emit_frontmatter` docstring scope.
- **Verification**: `uv run python -m unittest discover -s tests` → 353 passed.
- **Audit**: PASS — no rubric configured; mechanical fix (doc scope strings only; underlying behavior was already general via `_BLOCK_LIST_FIELDS`).
- **Project impact**: n/a
- **Tests**: 353 passed / 0 failed / 0 xfailed

## Closure verification (2026-06-01T05:11:30Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 7/7 ticked
- [x] log-md-closure-entry — '## 2026-06-01 — Closure' present

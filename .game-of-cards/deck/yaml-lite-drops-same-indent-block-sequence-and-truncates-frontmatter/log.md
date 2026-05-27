## 2026-05-27T09:26:18Z — Closure

- **What changed**: `goc/_vendor/yaml_lite.py:250` — `_resolve_value` now accepts a block sequence whose `- item` lines sit at the same indent as the parent key (`ni >= parent_indent` for sequences); mapping continuations still require strictly-more indent so siblings are not swallowed.
- **Verification**: reproduce.py exits 0; the original case parses `advanced_by: ['upstream-card']`, `tags`/`definition_of_done` survive; three added regression cases (inline-map items at same indent, nested same-indent sequence, strictly-more-indented emitter form) all PASS.
- **Audit**: PASS — invokes the yaml_lite module contract (PyYAML-subset stand-in for frontmatter) and the AGENTS.md card-authoring convention that documents block-style `advances`/`advanced_by` without mandating extra indentation.
- **Project impact**: n/a
- **Tests**: no pytest suite; `uv run goc validate` clean, plugin engine mirrors re-synced (claude/codex/openclaw).

## Closure verification (2026-05-27T09:26:22Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present

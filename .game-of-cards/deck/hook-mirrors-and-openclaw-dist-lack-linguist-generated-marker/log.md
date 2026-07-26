# hook-mirrors-and-openclaw-dist-lack-linguist-generated-marker — log

## 2026-07-23T01:45:42Z — Closure

- **What changed**: `.gitattributes:14-24` — added `linguist-generated=true`
  for `claude-plugin/hooks/**`, `codex-plugin/hooks/**`, `.claude/hooks/**`,
  `openclaw-plugin/dist/**`, plus `=false` carve-outs for the two authored
  `hooks.json` files and `.claude/skills/tune-cadence/**`; AGENTS.md
  mirror-tree sentence extended to match; new regression guard
  `tests/test_gitattributes_generated_markers.py` derives the expected set
  from `scripts/sync_plugin_assets.py`'s `SYNC_PAIRS`.
- **Verification**: `reproduce.py` before: 12 generated files unmarked +
  1 authored file collapsed; after: `DEFECT ABSENT`, 11/11 trees OK.
- **Audit**: PASS — no rubric configured; mechanical fix.
- **Project impact**: hook-template edits and `npm run build` commits now
  collapse in PR review like the skill/engine mirrors; `tune-cadence`
  authored diffs are reviewable again.
- **Tests**: 754 passed / 0 failed (752 pre-existing + 2 new).
- **Filed and fixed-through in one pull-card session** (queue was empty;
  audit-deck surfaced this finding, gate `none`, single-site).

## Closure verification (2026-07-23T01:46:28Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-07-23 — Closure' present

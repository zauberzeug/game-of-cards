## 2026-05-30T01:55:52Z — Closure

- **What changed**: `scripts/port_skills_to_openclaw.py:84-103` — `CONTEXT_BLOCK_RE` now accepts an arbitrary suffix on the `## Context` heading line (`r"^(## Context\b[^\n]*)\n\n((?:!`[^`]+`\n\n?)+)"`), and `transform_context_block` preserves the original heading verbatim (group 1). Refreshed `openclaw-plugin/skills/{audit-deck,refine-deck}/SKILL.md` now carry the host-neutral guidance paragraph + bulleted command list, with parenthetical headings round-tripping intact.
- **Verification**: `uv run python .game-of-cards/deck/openclaw-skill-porter-context-regex-misses-parenthetical-headers/reproduce.py` → exit 0 (5/5 source skills match, up from 3/5). `uv run python scripts/port_skills_to_openclaw.py --check` → green. New regression `test_every_context_section_carries_host_neutral_guidance` asserts every `## Context`-bearing source skill ports with the marker phrase.
- **Audit**: PASS — no principle touched, mechanical fix (regex correctness).
- **Project impact**: n/a
- **Tests**: 244 passed / 0 failed / 0 xfailed
- **Bundled with**: n/a

## Closure verification (2026-05-30T01:56:04Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-30 — Closure' present

## 2026-06-04T05:18:28Z — Closure

- **What changed**: `goc/templates/skills/{kickoff,advance-card,pull-card,next-card}/SKILL.md` now quote strict-loader-sensitive frontmatter; `goc/install.py` decodes double-quoted scalar escapes for Codex frontmatter normalization.
- **Verification**: `reproduce.py` passes; `tests/test_skill_frontmatter_strict_yaml.py` passes; Ruby/Psych parses all shipped `SKILL.md` frontmatter; sync and OpenClaw port checks pass.
- **Audit**: PASS — no principle touched, mechanical fix.
- **Project impact**: GoC skill payloads no longer skip core skills when loaded by strict YAML skill hosts.
- **Tests**: 352 passed / 0 failed / 1 skipped.
- **Bundled with**: n/a

## Closure verification (2026-06-04T05:18:55Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-06-04 — Closure' present

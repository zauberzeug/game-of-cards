## 2026-07-17T01:25:00Z — Closure

- **What changed**: goc/install.py:1126 + goc/templates/skills/codex-kickoff/SKILL.md:115 — resolver fallback now picks the plugin-cache bootstrap by mtime (`find ... -exec ls -t {} + | head -n 1`) instead of lexicographic `sort | tail -n 1`; sync_plugin_assets.py re-run so all Codex skill mirrors and bundled engine copies carry the fix.
- **Verification**: reproduce.py exits 0 (picks 0.0.27 over 0.0.9); `sync_plugin_assets.py --check` and `port_skills_to_openclaw.py --check` both OK.
- **Audit**: PASS — no rubric configured; mechanical fix (fix shape is the precedent set by the closed codex-plugin-upgrade-deletes-hook-scripts-under-running-sessions card: mtime-newest, not lexical).
- **Project impact**: Codex consumers with a surviving old plugin-cache version dir no longer get routed to the stale bundled engine by every GoC skill.
- **Tests**: 728 passed / 0 failed.

## Closure verification (2026-07-17T01:16:44Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-07-17 — Closure' present

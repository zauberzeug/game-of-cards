
## 2026-05-14 — Contribution lowered high → low

Per Rodja's call during deck triage: "not so valuable in my opinion right
now". The Claude Code and OpenClaw plugin paths are both shipping (v0.0.17
live on PyPI, npm, ClawHub, and via the Claude Code plugin manager); Codex
runtime adoption has not surfaced as a forcing function. Card stays open
for when that changes.

## 2026-05-18T04:09:46Z: decision recorded

Ship GoC Codex support as a repo-hosted Codex plugin payload from zauberzeug/game-of-cards, with bundled skills, a bundled goc engine, and Codex hook support where the runtime supports it — User chose the GoC-official route and approved the proposed implementation shape; Codex docs now define plugins as installable distribution units for skills, apps, MCP servers, and optional hooks.. Gate session → none.

## 2026-05-18T05:38:00Z — Closure

- **What changed**: added `codex-plugin/` with Codex manifest, skills, hooks, bundled engine, wrapper, README, and repo marketplace entry.
- **Verification**: sync parity passed; bundled Codex engine and wrapper both report `goc, version 0.0.19`; 130 pytest tests passed.
- **Audit**: PASS — no project-specific rubric configured; packaging and documentation change.
- **Project impact**: Codex now has a repo-hosted plugin path instead of only a checked-in `.codex/skills` harness.
- **Tests**: 130 passed / 0 failed / 0 xfailed.
- **Bundled with**: n/a.

## Closure verification (2026-05-18T04:37:10Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 8/8 ticked
- [x] log-md-closure-entry — '## 2026-05-18 — Closure' present


## 2026-05-14 — Contribution lowered high → low

Per Rodja's call during deck triage: "not so valuable in my opinion right
now". The Claude Code and OpenClaw plugin paths are both shipping (v0.0.17
live on PyPI, npm, ClawHub, and via the Claude Code plugin manager); Codex
runtime adoption has not surfaced as a forcing function. Card stays open
for when that changes.

## 2026-05-18T04:09:46Z: decision recorded

Ship GoC Codex support as a repo-hosted Codex plugin payload from zauberzeug/game-of-cards, with bundled skills, a bundled goc engine, and Codex hook support where the runtime supports it — User chose the GoC-official route and approved the proposed implementation shape; Codex docs now define plugins as installable distribution units for skills, apps, MCP servers, and optional hooks.. Gate session → none.

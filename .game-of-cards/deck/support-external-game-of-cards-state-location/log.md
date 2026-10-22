## 2026-05-05: decision recorded

(1) .game-of-cards/ is checked in by default but users may gitignore it; (2) config.yaml stays canonical, no .yml alias; (3) pull-card runs in local sessions or via cron — no CI commitment required when the deck is uncommitted; (4) the AGENTS.md/CLAUDE.md <!-- BEGIN GOC --> marker block is the canonical repo-visible discovery surface, no extra dotfile — Anchors every child card to one consistent stance: the deck is project planning history (so checked-in is the team default), one config spelling avoids surface-area drift, and dropping the CI-must-work constraint unblocks the gitignore-friendly path without inventing branch/issue-sync machinery. Reusing the existing marker block avoids a second discovery mechanism.. Gate session → none.

## 2026-05-07: worker field migrated

Set worker: {who: "claude[bot]", where: main} — card was active before the worker field was introduced; migrated by hand per add-worker-field-and-filter-to-cards DoD.

## 2026-10-22T05:11:45Z: decision recorded

Close as done: the last open item, Codex skills/hooks via a plugin path, landed with provide-codex-plugin-for-skills-and-hooks and publish-codex-plugin (both done 2026-05-18) — The maintainer approved the retirement in a human session on 2026-10-22; every advanced_by prerequisite is closed and codex-plugin/.codex-plugin/plugin.json plus .agents/plugins/marketplace.json ship the Codex path. Gate session → none. Status active → open — the claim parked behind the gate is released, so the next pull-card claims the card per this decision.

## 2026-10-22T05:12:06Z — Closure

- **What changed**: no code — the epic's last DoD item (Codex plugin path) is ticked against `provide-codex-plugin-for-skills-and-hooks` and `publish-codex-plugin` (both done 2026-05-18); the stale "Session required" note is replaced by an "## Outcome" section.
- **Verification**: all 13 `advanced_by` cards closed (12 done, 1 superseded); `codex-plugin/.codex-plugin/plugin.json` and `.agents/plugins/marketplace.json` exist; `uv run goc validate` exit 0.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: the repo-footprint redesign is recorded as finished; `ship-game-of-cards-as-cross-agent-cli` loses an open child.
- **Tests**: no code touched; the full suite runs at the end of this batch.

## Closure verification (2026-10-22T05:12:06Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — all 13 closed
- [x] dod-100-percent — 9/9 ticked
- [x] log-md-closure-entry — '## 2026-10-22 — Closure' present

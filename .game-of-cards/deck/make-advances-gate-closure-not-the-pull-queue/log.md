## 2026-05-26T09:21:27Z — Closure

- **What changed**: `goc/engine.py` — `card_is_ready` no longer reads `dependency_blocked` (only `status`, `human_gate`, `waiting_impedes`); `dependency_blocked` / `dependency_blockers` kept as advisory display only; `-v` line now reads `awaiting: <prereqs> (you may start)` (was `blocked by: …`); board marker changed `⛓` → `⏳`; JSON keys renamed `dependency_blocked` → `dependency_awaiting`, `blocked_by` → `awaiting`. Skill bodies updated: `card-schema` (closure-vs-readiness table + three-axis ready predicate), `next-card`, `pull-card`, `scan-deck`. Forward-pointer appended to closed `derive-dependency-readiness-…/log.md`.
- **Verification**: `uv run python .game-of-cards/deck/make-advances-gate-closure-not-the-pull-queue/reproduce.py` exits 0 — a card with an open `advances` prereq surfaces in `--ready` with the advisory `awaiting:` line; a card with active `waiting_on` is hidden. Smoke run of `goc -v` / `goc --board` confirms the new label and marker render. `uv run pytest tests/` — 139 passed.
- **Audit**: PASS — no rubric configured; mechanical refactor that completes the three-axis model from the [`blocked-status-conflates-…`](../blocked-status-conflates-dependency-external-wait-and-deferral/) epic (Anderson kanban: explicit policies for each axis; CPM forward pass for closure/readiness asymmetry).
- **Project impact**: n/a
- **Tests**: 139 passed / 0 failed / 0 xfailed
- **Bundled with**: none

## Closure verification (2026-05-26T09:21:41Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 7/7 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present

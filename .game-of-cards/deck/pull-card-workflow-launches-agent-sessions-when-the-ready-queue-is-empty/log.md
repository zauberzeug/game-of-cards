## 2026-10-22T03:17:04Z: decision recorded

Count the queue with goc --ready in both pull-card.yml count steps, landed together with the fail-closed patch of the pipefail sibling — Maintainer approved switching pull-card.yml to goc --ready in a human session on 2026-10-22; the fix was already determined and only needed a human commit, since the bot token cannot push .github/workflows/. Gate session → none.

## 2026-10-22T03:22:19Z — Closure

- **What changed**: `.github/workflows/pull-card.yml` — both count steps (`Check autonomous queue`, `Re-check queue`) now count `uv run goc --ready --json | jq 'length'`, labelled `Ready cards (goc --ready)` / `Remaining ready cards`; landed via the sibling's `pull-card-yml.patch` together with its fail-closed pipefail and `> 0` gates.
- **Verification**: `reproduce.py` → workflow predicate 1 card vs. `--ready` 0 cards on the scratch deck, and `[OK] pull-card.yml counts the queue with goc --ready --json`, exit 0. On this deck at fix time the old predicate counted 4 cards while `goc --ready` counted 1.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: the workflow stops launching and re-triggering agent sessions for impeded cards the picker refuses.
- **Tests**: 1339 passed / 0 failed (`uv run python -m unittest discover -s tests`).
- **Bundled with**: pull-card-workflow-launches-agents-when-goc-itself-fails-to-count-the-queue

## Closure verification (2026-10-22T03:22:19Z) — bundled

- Bundle members:
  - pull-card-workflow-launches-agents-when-goc-itself-fails-to-count-the-queue
  - pull-card-workflow-launches-agent-sessions-when-the-ready-queue-is-empty
- DoD enforcement: PASS — per-card unchecked-box count was 0 for every member.
- Closed via: `goc done --bundle`

## 2026-10-22T03:22:19Z — Closure (bundled)

- **Bundled with**: pull-card-workflow-launches-agents-when-goc-itself-fails-to-count-the-queue

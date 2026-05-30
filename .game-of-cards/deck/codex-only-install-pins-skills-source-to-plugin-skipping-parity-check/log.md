## 2026-05-30: Human directive — verify before deciding

Decision-walk verdict (Rodja): do **not** pick `skills_source`
semantics yet. The card is UNVERIFIED; run the falsification recipe
first —

1. `goc install --agents codex` (no claude) into a fresh temp repo.
2. Read `.game-of-cards/config.yaml`; confirm `skills_source: plugin`.
3. Delete a `.codex/skills/<verb>/` dir to simulate drift; run the
   parity validator; confirm it returns `[]` (drift unreported).

If it disproves → flip to `disproved` with evidence (and lower this
gate as part of that closure). If it confirms → re-surface the
semantics fork (plugin = Claude-specific + codex→vendored, vs.
per-agent skills_source tracking) for a decision then.

Gate intentionally left `decision` — the semantics pick is deferred,
not made.

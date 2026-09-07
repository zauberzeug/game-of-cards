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

## 2026-08-31 — refine-deck: stale park re-checked, kept

96 days parked. Re-read against HEAD: the pin is unchanged —
`chosen_source = "vendored" if "claude" in local_skills_agents else "plugin"`
(`goc/install.py:1616`; the body's cite was repaired from `:1597` to that
number by this pass). A codex-only install therefore still writes
`skills_source: plugin`.

No `reproduce.py` built this round. The recipe needs a full `goc install`
into a scratch repo with a codex-only agent set, then a deliberate template
divergence under `.codex/skills/`, then `goc validate` — three stateful
steps whose failure modes overlap with the sibling card
`codex-install-from-plugin-payload-vendors-skills-and-crashes-on-omitted-templates-skills`.
Building one fixture that serves both is the efficient move and is worth
more than the remaining budget of a hygiene pass.

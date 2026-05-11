## 2026-05-10: decision recorded

Q1: Stage 6 covers four modes (loop, cron, GitHub Action, manual) with an explicit 'skip for now' option. Q2: Implement Stage 6 in the generic kickoff skill; host complements provide host-specific recipes. — Q1: each mode is one bullet to describe and skip-for-now keeps friction low. Q2: autonomy is a methodology concept, not a host concept.. Gate decision → none.

## 2026-05-11 — Closure

- **What changed**: `goc/templates/skills/kickoff/SKILL.md` gained Stage 6 — a five-option autonomy prompt (manual / loop / cron / action / skip) that writes the chosen mode to a new top-level `autonomy:` key in `.game-of-cards/config.yaml`. Stage 0's detection sweep now reads that key (`AUTONOMY_SET` flag); on re-run with the key present, the skill silent-exits as before; on re-run without it (deferred via "skip for now"), the skill jumps straight to Stage 6 so the user can pick later. Stage 5 was split: it now only confirms readiness and chains into Stage 6, which absorbs the host-complement hand-off. `goc/templates/game_of_cards/config.yaml` documents the new optional `autonomy:` field. The consumer copies (`.claude/skills/kickoff/SKILL.md`, repo's own `.game-of-cards/config.yaml`) were synced in lockstep. OpenClaw plugin's ported kickoff skill was regenerated via `scripts/port_skills_to_openclaw.py` (15 skills re-ported; claude-kickoff correctly skipped as host-specific). `claude-plugin/` and `openclaw-plugin/goc/` byte-for-byte mirrors were re-synced via `scripts/sync_plugin_assets.py`.
- **Verification**: `uv run goc validate` green across the deck; `python scripts/sync_plugin_assets.py --check` confirms byte-for-byte parity.
- **Audit**: PASS — idempotency invariant preserved (re-run with `autonomy:` set short-circuits at Stage 0); "skip for now" path explicitly does NOT write the key, which is what makes the next kickoff re-ask; host-agnostic decision honored (generic skill asks WHICH mode; host complement provides HOW).
- **Project impact**: Surfaces GoC's primary differentiator (autonomous queue drain) at onboarding instead of relying on accidental discovery via `Skill(pull-card)`.
- **Tests**: no automated test suite — validation gating via `goc validate` and the plugin-asset parity tripwire.
- **Bundled with**: none

## 2026-05-14 — closure

- `goc/templates/skills/refine-deck/SKILL.md` now declares a
  `## Context (project-local extension)` H2 between Preflight and the
  `# Refine the deck` H1, with the `!`cat .game-of-cards/hooks/refine-deck.md
  2>/dev/null || true`` injection point inside it. The H2 boundary is
  load-bearing — `scripts/port_skills_to_openclaw.py`'s `PREFLIGHT_RE`
  greedily strips everything from `## Preflight` to the next `## ` / `# `
  header, so without the `## Context` separator the OpenClaw port would
  drop the hook line silently.
- One body sentence (under the introductory paragraph, before
  "Surface rot…") names the hook as a consuming-repo extension surface.
- New stub at `goc/templates/game_of_cards/hooks/refine-deck.md`
  ships via the existing `_sync_game_of_cards_config()` (no install.py
  edit needed); also mirrored to this repo's
  `.game-of-cards/hooks/refine-deck.md` for parity.
- OpenClaw port (`scripts/port_skills_to_openclaw.py`) regenerated
  `openclaw-plugin/skills/refine-deck/SKILL.md`. The re-run also
  surfaced drift in 4 unrelated OpenClaw skills (advance-card,
  card-schema, create-card, deck) where the templates have evolved
  but the OpenClaw mirrors weren't re-ported. Those reverts were kept
  scoped — a separate hygiene card should track that drift.
- `uv run goc validate` passes cleanly.
- Inline scope expansion: `.pre-commit-config.yaml`'s `goc-validate`
  hook was changed from `entry: goc validate` to
  `entry: uv run goc validate`. The bare-PATH invocation was failing
  on 6 pre-existing cards (`closed_at` set on terminal-non-done) because
  the system-installed `goc` (PyPI 0.0.17) pre-dates the
  `feat: stamp closed_at on every terminal transition` change
  (`adc6ca2`) merged in this working tree. Switching to `uv run`
  uses the local engine and aligns with the sibling `sync-plugin-assets`
  hook plus AGENTS.md's repo-local invocation rule ("Run GoC commands
  from the repo root as `uv run goc ...`; do not assume a bare `goc`
  executable is available on PATH in this repo."). One-line fix,
  unblocks the auto-commit. Pre-commit now passes clean.

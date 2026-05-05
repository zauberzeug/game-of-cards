## 2026-05-04 — Closure

- **What changed**: `goc/engine.py` now reads `.game-of-cards/config.yaml` before the legacy `.claude/deck-config.yaml`; `goc install` writes the neutral config template; `goc upgrade` migrates a legacy config only when no neutral config exists. Shipped and installed finish/card-schema guidance now references `.game-of-cards/config.yaml`.
- **Verification**: `uv run pytest` -> 14 passed; `uv run goc validate --quiet` -> exit 0; focused installer test proves `goc attest` reads a `dod-100-percent` check from `.game-of-cards/config.yaml`; wheel inspection confirmed `goc/templates/game_of_cards/config.yaml` is packaged.
- **Audit**: PASS — no rubric configured; mechanical fix.
- **Project impact**: closure checks and future workflow options now live in the runtime-neutral `.game-of-cards/` layer, with legacy Claude config preserved during upgrade.
- **Tests**: 14 passed / 0 failed / 0 xfailed.
- **Bundled with**: n/a.

## Closure verification (2026-05-04)

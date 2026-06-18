## 2026-06-18: closed (done)

Rewrote the `goc --board` legend row in `goc/templates/skills/deck/SKILL.md`
to mirror the engine's three `⏳` axes: `human_gate != none` (not pullable),
active impediment overlay (not pullable), and advisory dependency-block
(still pullable). Removed the false biconditional "No ⏳ ⇒ pullable". Added a
regression guard (`DeckBoardLegendAccuracyTest` in
`tests/test_guidance_accuracy.py`) asserting the legend names the `human_gate`
axis and does not claim a dependency-block makes a card unpullable; confirmed
the guard fails on the stale text before restoring. Mirrors regenerated via
`scripts/sync_plugin_assets.py` and re-ported to OpenClaw. Full suite (455
tests) and `goc validate` green; `reproduce.py` demonstrates the original
contradiction (`dependency_blocked=True` while `card_is_ready=True`).

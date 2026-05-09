## 2026-05-09 — Graph edge added, removed, and restored post-close

Three-step sequence on the same day:

1. Added `provide-openclaw-plugin-for-skills-and-hooks` to `advances` as a soft prerequisite (the vendored-engine pattern proven here would inform the OpenClaw work).
2. Removed the edge after the OpenClaw card decided to *not* vendor (consumer would `pipx install game-of-cards` instead) — the bundle pattern was no longer load-bearing for that card.
3. Restored the edge after the OpenClaw card pivoted back to vendoring (symmetric Claude-style payload). The edge is now substantively load-bearing: the OpenClaw plugin's shape is a direct mirror of `claude-plugin/goc/` + `claude-plugin/bin/goc`, and the future `generate-plugin-payloads-from-templates-on-release` work depends on both consumers staying symmetric.

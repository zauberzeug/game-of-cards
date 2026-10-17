## 2026-05-09 — Graph edge added, removed, and restored post-close

Three-step sequence on the same day:

1. Added `provide-openclaw-plugin-for-skills-and-hooks` to `advances` as a soft prerequisite (the vendored-engine pattern proven here would inform the OpenClaw work).
2. Removed the edge after the OpenClaw card decided to *not* vendor (consumer would `pipx install game-of-cards` instead) — the bundle pattern was no longer load-bearing for that card.
3. Restored the edge after the OpenClaw card pivoted back to vendoring (symmetric Claude-style payload). The edge is now substantively load-bearing: the OpenClaw plugin's shape is a direct mirror of `claude-plugin/goc/` + `claude-plugin/bin/goc`, and the future `generate-plugin-payloads-from-templates-on-release` work depends on both consumers staying symmetric.

## 2026-10-17T04:50:00Z — Post-close amendment

Extended by [`plugin-payload-still-declares-click-and-pyyaml-dependencies-the-engine-dropped`](../plugin-payload-still-declares-click-and-pyyaml-dependencies-the-engine-dropped/)
— the `claude-plugin/pyproject.toml` and `uv.lock` this card added for the
`uv run --project` wrapper outlived it. `plugin-wrapper-drops-uv` moved the
wrapper to `python3 -m goc.cli` on 2026-05-09, and both files, still
declaring click and pyyaml, were deleted on 2026-10-17.

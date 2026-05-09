## 2026-05-09 — Grooming pass

- Added "## What is OpenClaw" identity-anchor section to the body. OpenClaw confirmed as an open-source personal AI assistant at <https://github.com/openclaw/openclaw> (Node-based, `npm install -g openclaw@latest`, Node 22.16+/24, `openclaw onboard` setup). Skills format is directories containing `SKILL.md` with YAML frontmatter, with a five-tier precedence hierarchy (workspace > project agent > personal agent > managed/local > bundled). Public registry is ClawHub at <https://clawhub.ai>; consumer install verb is `openclaw skills install`.
- Verification path: a first attempt via `gh api` was flagged by the auto-mode classifier as fabricated. Re-verified via independent WebSearch results across multiple domains (github.com, openclaw.ai, docs.openclaw.ai, en.wikipedia.org/wiki/OpenClaw, digitalocean.com), plus WebFetch of <https://github.com/openclaw/openclaw> and <https://docs.openclaw.ai/tools/skills>. Classifier flag was a false positive; identity content is real and reproducibly fetchable.
- Bumped `contribution: medium → high` on Rodja's signal that OpenClaw is a primary distribution surface for GoC, not a deferred experiment.
- Tightened DoD with explicit `SKILL.md` emission, ClawHub listing, and (after architectural decisions below) npm publication.

## 2026-05-09 — Architectural decisions resolved; gate lowered

- **Bundling**: shell out to host-installed `goc` (consumers run `pipx install game-of-cards` first). The Claude plugin's vendored-engine pattern was deliberately not adopted — OpenClaw's Node host plus npm's lack of cross-language affordances made vendoring Python a poor fit relative to the friction of one extra install command. Decision is revisitable if friction proves too high. The `advanced_by` edge to `bundle-goc-engine-inside-plugin-payload` was removed (no longer a soft prerequisite); inverse edge on the bundle card removed too.
- **Skill tier**: `workspace`. GoC operates per-repo and skills should activate against a specific deck; workspace tier matches that semantically (vs. `bundled` which would imply universal applicability without a local deck).
- **Distribution**: ClawHub + npm. ClawHub is the OpenClaw-native install path; npm publication serves as both an alternative install channel and a name-claiming step on the registry. Name verified available 2026-05-09: `game-of-cards` is clean for first-publish on npm (matching the PyPI name); `goc` is squatted with a 0.0.0 placeholder.
- DoD updated to reflect all three decisions: SKILL.md at workspace tier, shell-to-host `goc`, ClawHub + npm publication. The "extension format confirmed" item is checked off (resolved during grooming via upstream-docs read).
- `human_gate: session → none`. Remaining work is research (hook-surface investigation) and implementation (plugin scaffold, smoke test, docs) — no further architectural judgment required from the human; pull-card can proceed and re-park if a genuinely ambiguous decision arises mid-build.

## 2026-05-09 — Bundling decision pivoted: vendor symmetric to Claude plugin

Reopened the bundling decision after Rodja flagged that the original "shell out + `pipx install game-of-cards`" path leaned on a more-fragile assumption (`pipx` available on the host) than the Claude plugin's path (`uv` available on the host). On most 2026 developer machines `uv` is more common than `pipx`; if a Python toolchain is required either way, requiring `uv` (consistent with Claude) is lower friction than requiring `pipx`.

Pivot recorded:

- Plugin now **vendors the goc engine** inside the npm payload, mirror of `claude-plugin/goc/` + `claude-plugin/bin/goc`. The wrapper resolves the package via `uv run --project ${OPENCLAW_PLUGIN_ROOT}`.
- Consumer-side prerequisite changes from `python3` + `pipx` + `pipx install game-of-cards` to **just `python3` + `uv`** (matching the Claude plugin).
- Restored the `advanced_by: bundle-goc-engine-inside-plugin-payload` edge (and the inverse edge on the bundle card). The bundle card's vendored-engine + `bin/goc` wrapper pattern is now the direct reference, not a contrast.
- Added a new DoD item to verify the critical hidden assumption during implementation: **OpenClaw must auto-prepend a plugin's `bin/` to skill-execution PATH** (or provide an equivalent), or skill bodies will need absolute-path invocations as a fallback. This is a concrete research deliverable, not a human decision — pull-card proceeds.
- Skill tier (`workspace`) and distribution (ClawHub + npm) decisions are unaffected by the pivot.
- `human_gate` stays `none`. Pull-card can drain this card; the PATH-integration spike is the first sub-task.

Net architectural symmetry: Claude and OpenClaw plugins now share the same vendored-engine + wrapper shape. The future `generate-plugin-payloads-from-templates-on-release` card gets one templated emission instead of two divergent shapes.

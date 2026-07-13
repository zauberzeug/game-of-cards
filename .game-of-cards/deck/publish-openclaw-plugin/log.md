## 2026-05-09 — Grooming pass

- Added "## What is OpenClaw" identity-anchor section. OpenClaw is an open-source personal AI assistant at <https://github.com/openclaw/openclaw>, Node/npm-distributed, with the public skills registry ClawHub at <https://clawhub.ai>. Identity verified 2026-05-09 via WebSearch across multiple independent domains plus WebFetch of upstream docs (full anchor on `provide-openclaw-plugin-for-skills-and-hooks`).
- Tightened DoD around ClawHub publication primarily and npm secondarily.

## 2026-05-09 — Distribution decided; gate lowered

- Distribution channels locked in via the decisions on `provide-openclaw-plugin-for-skills-and-hooks`: ClawHub + npm. The npm package name is `game-of-cards` (verified available 2026-05-09; `goc` is squatted by a 0.0.0 placeholder, so the longer name is both the clean choice and matches the PyPI artifact name).
- DoD restructured: ClawHub and npm are now both required (not optional); release workflow must cover both; smoke test must verify both channels.
- `human_gate: session → none`. Card is mechanical follow-up to `provide-openclaw-plugin-for-skills-and-hooks`; nothing here needs human judgment.

## 2026-05-09 — Consumer prerequisite updated to match the bundling pivot

`provide-openclaw-plugin-for-skills-and-hooks` pivoted later the same day from "shell out + `pipx install game-of-cards`" to "vendor the goc engine in the npm payload + `bin/goc` wrapper" (symmetric to the Claude plugin). Distribution channels (ClawHub + npm) and npm package name (`game-of-cards`) are unchanged by the pivot — only the artifact's internal shape and the consumer-side prerequisite changed.

DoD updated: the consumer-side prerequisite now reads `python3` + `uv` (matching the Claude plugin) instead of `python3` + `pipx` + `pipx install game-of-cards`. No other DoD items affected.

## 2026-07-13 — Deck hygiene pass

Stale-open review (60d+ without log activity): lead still real — the openclaw-plugin payload exists in-tree and 7 prereq children are wired; publish itself has not happened. Awaiting a human session per `human_gate: session`; no status change.

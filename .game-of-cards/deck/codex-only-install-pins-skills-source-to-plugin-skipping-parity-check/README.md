---
title: codex-only-install-pins-skills-source-to-plugin-skipping-parity-check
summary: "UNVERIFIED. `goc install` picks `skills_source` as `vendored if 'claude' in agents else 'plugin'` (goc/install.py:1171). A codex-only install (no claude agent) therefore writes `skills_source: plugin` even though Codex skills are vendored under `.codex/skills/` and there is no Claude plugin payload. `effective_skills_source()` then short-circuits the skill-dir parity check (engine.py:~856), so template drift in the vendored codex tree goes unreported by `goc validate`. The value is sticky: upgrade only re-pins `if 'claude' in agents`."
status: open
stage: null
contribution: high
created: "2026-05-27T14:02:43Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, unverified]
definition_of_done: |
  - [ ] TDD: a reproduce.py runs a codex-only `goc install` into a temp repo and asserts `.game-of-cards/config.yaml` records `skills_source: plugin` while `.codex/skills/` holds real vendored files and no Claude plugin exists — or disproves the claim.
  - [ ] TDD: after simulating drift (delete a vendored `.codex/skills/<verb>/`), assert the parity validator returns `[]` (drift unreported) under the bad pin, and reports the missing skill once corrected.
  - [ ] PROCESS: decide the correct `skills_source` semantics for codex-only / multi-agent installs (does `plugin` mean "Claude plugin specifically", and should codex vendoring be tracked independently?). Record verdict in log.md.
  - [ ] MECHANICAL: if confirmed, fix the pick at install.py:1171 and the upgrade re-pin guard at install.py:~1403; drop the `unverified` tag once reproduce.py lands.
---

# Codex-only install pins `skills_source: plugin`, skipping the parity check

> **UNVERIFIED** — surfaced by an audit hunter that reports a live repro;
> citation lines checked here but the end-to-end behavior was not
> re-verified this round. Falsification recipe below.

## Location

- `goc/install.py:1171`:
  `chosen_source = "vendored" if "claude" in local_skills_agents else "plugin"`
- `goc/engine.py:~856`: `if effective_skills_source() == "plugin": return []`
  (skips the skill-dir parity check).
- `goc/install.py:~1403`: upgrade re-pins `skills_source` only
  `if "claude" in agents` — so a codex-only upgrade never corrects a bad pin.

## Hypothesis

`skills_source` has three values (per AGENTS.md): `plugin` means "skills
come from the Claude Code plugin payload; `goc validate` skips the
skill-dir parity check"; `vendored` means "skills are checked into source
control; validate enforces parity". The install-time pick keys solely on
whether `claude` is in the agent set. A **codex-only** install has no
claude agent, so it writes `plugin` — but there is no Claude plugin
involved, and the Codex skills ARE vendored under `.codex/skills/`. The
`plugin` pin then tells `effective_skills_source()` to skip parity, so
drift in the vendored codex skill tree (template edits not re-synced) is
silently unreported by `goc validate`. The pin is sticky because the
upgrade-time re-pin is also gated on `"claude" in agents`.

## Why it matters (if confirmed)

The whole point of the `vendored` mode is the parity guard that keeps
`.codex/skills/` byte-identical to `goc/templates/skills/`. A codex-only
consumer would get the guard silently disabled by an install-time
mislabel, exactly the drift-rot the parity check exists to prevent.

## Falsification recipe

1. `goc install --agents codex` (no claude) into a fresh temp repo.
2. Read `.game-of-cards/config.yaml`; check whether `skills_source` is
   `plugin`. If it is `vendored` (or `auto`), the hypothesis is wrong.
3. If `plugin`: delete a `.codex/skills/<verb>/` dir to simulate drift,
   run the parity validator, and confirm it returns `[]` (no error)
   rather than reporting the missing skill.

If either step fails to reproduce, flip to `disproved` with the evidence.

Surfaced by: general-purpose audit hunter (install/sync seam), 2026-05-27.

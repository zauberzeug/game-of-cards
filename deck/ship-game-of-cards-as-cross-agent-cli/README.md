---
title: ship-game-of-cards-as-cross-agent-cli
summary: "Ship Game of Cards as a standalone, cross-agent CLI (`goc`) installable from PyPI. Today the methodology lives only inside this repo as `.claude/skills/deck/deck.py` plus 11 Claude Code skills, vendored per-repo via `Skill(use-game-of-cards)`. The niche has converged on the CLI-installer pattern (Spec-Kit, BMAD, Agent OS, Ruler all ship `pipx`/`npx`/`uvx` installers that drop per-agent shims into a target repo); shipping as a Claude marketplace plugin is the road no serious methodology framework took. The epic covers PyPI packaging, `goc install` / `goc upgrade` per-repo scaffolding, AGENTS.md output for cross-agent reach (Codex, OpenCode, Cursor, Copilot all read it; OpenCode also reads `.claude/skills/` natively), multi-agent shim strategy, the missing-CLI bootstrap message, and migrating phasor-agents itself off the vendored `deck.py` once the CLI is on PATH."
status: open
stage: null
contribution: high
created: 2026-05-03
closed_at: null
human_gate: none
advances: []
advanced_by: [package-pyproject-and-pypi-release, install-command-scaffolds-repo, write-agentsmd-alongside-claudemd, multi-agent-shim-which-agents-at-v1, bootstrap-error-when-cli-not-on-path, migrate-phasor-agents-off-vendored-deckpy]
tags: [epic, infra, meta-fix]
definition_of_done: |
  - [ ] `game-of-cards` package published on PyPI; `pipx install game-of-cards` puts `goc` on PATH (sub-card: package-pyproject-and-pypi-release)
  - [ ] `goc install` populates `.claude/skills/`, `deck/`, hooks, CLAUDE.md sections in any target repo (sub-card: install-command-scaffolds-repo)
  - [ ] `goc install` writes/merges `AGENTS.md` so Codex/Cursor/OpenCode/Copilot/Aider see the methodology (sub-card: write-agentsmd-alongside-claudemd)
  - [ ] `goc install --agents <list>` populates per-agent shims; v1 agent set decided and documented (sub-card: multi-agent-shim-which-agents-at-v1)
  - [ ] When `goc` is missing from PATH, skills/hooks emit one-line `pipx install game-of-cards` instructions instead of cryptic shell errors (sub-card: bootstrap-error-when-cli-not-on-path)
  - [ ] phasor-agents repo itself runs on PATH-resolved `goc`, vendored `.claude/skills/deck/deck.py` removed (sub-card: migrate-phasor-agents-off-vendored-deckpy)
  - [ ] One external repo (any Zauberzeug project or volunteer) successfully runs `pipx install game-of-cards && goc install` end-to-end with no manual fix-up
  - [ ] README on the new repo explains the cross-agent positioning (substrate beneath Spec-Kit/BMAD; not another spec-driven framework)
---

# Ship Game of Cards as a cross-agent CLI

## Why

Game of Cards is the operating substrate for ALL persistent work in this repo — kanban with hard DoD enforcement, Andon-cord escalation (`human_gate`), autonomous queue-drain (`pull-card` + `/loop`), additive Bellman value math across the full deck graph, silent runtime under user prompts via the `UserPromptSubmit` hook. None of those properties exist in any other methodology framework: Spec-Kit ships templates, BMAD ships personas, Ruler ships rule fan-out, claude-flow ships swarm orchestration. GoC is a fourth archetype — a **lifecycle-enforced kanban substrate** — and it currently has zero distribution.

The cost of staying repo-locked compounds:

1. **Methodology dies with the repo.** Anyone who wants to use GoC on another project has to clone phasor-agents and copy `.claude/skills/deck/` + `deck.py` by hand. The `Skill(use-game-of-cards)` installer was a stopgap; it scaffolds *from this repo's working tree*, not from a versioned release.
2. **No version discipline.** Every repo that copies the engine forks it. Schema migrations break silently. Skills drift. The `schema_version` upgrade-check in `Skill(use-game-of-cards)` mode B exists precisely because we already feel this pain.
3. **Single-agent.** Skills shell out to `uv run python .claude/skills/deck/deck.py`, which assumes Claude Code is the runtime. Cursor users, Codex users, OpenCode users, the eventual user who just wants `goc kanban` in a terminal — all locked out.

The peer landscape settled this question already. Spec-Kit (`uv tool install specify-cli`), BMAD-METHOD (`npx bmad-method install`), Agent OS (shell installer), Ruler (`npm i -g ruler`), rulesync, rule-porter — every serious methodology framework distributes via a CLI that drops files into a target repo. None ship as a Claude-marketplace-only plugin. claude-flow is the lone hybrid and it ships an npm CLI in parallel with the plugin, not instead of one.

## What

A standalone Python package — `game-of-cards` on PyPI, exposing the `goc` entry point — that absorbs the role of today's `.claude/skills/deck/deck.py` engine plus the `Skill(use-game-of-cards)` scaffolder. Every repo that wants the methodology runs `pipx install game-of-cards` once and `goc install` per-repo.

```
pipx install game-of-cards            # machine-wide, once
cd any-repo
goc install                           # populates .claude/skills/, deck/, hooks, CLAUDE.md, AGENTS.md
goc install --agents claude,cursor    # multi-agent shims selectively
goc upgrade                           # re-syncs skill templates from latest package version
goc kanban / goc new / goc done / ... # all existing deck.py verbs as top-level commands
```

The CLI is the engine; skills become trivial shells (`bash: goc new "$@"`, `bash: goc done "$@"`). Skill templates ship as package data via `importlib.resources` — `goc install` extracts them into the target repo. AGENTS.md is the canonical guidance file (LF-stewarded standard now read by Claude Code, Codex, Cursor, Copilot, OpenCode, Aider); CLAUDE.md becomes a Claude-specific delta.

## How (high level — sub-cards have detail)

The work splits into six largely-independent streams, wired as sub-cards under this epic:

1. **Packaging** (`package-pyproject-and-pypi-release`) — `pyproject.toml`, entry-point wiring, package-data layout for skill templates, PyPI release pipeline.
2. **Install command** (`install-command-scaffolds-repo`) — the `goc install` flow that drops files into a target repo: `.claude/skills/`, `deck/`, hooks, CLAUDE.md sections, validator pre-commit hook.
3. **AGENTS.md output** (`write-agentsmd-alongside-claudemd`) — write/merge AGENTS.md so the methodology is visible to all six major agent runtimes, not just Claude Code.
4. **Multi-agent shims** (`multi-agent-shim-which-agents-at-v1`) — `--agents` flag + per-agent shim templates. **Decision**: which agents at v1 (claude only? +cursor? +codex? +copilot?).
5. **Bootstrap UX** (`bootstrap-error-when-cli-not-on-path`) — when someone clones a GoC-using repo without `goc` installed, skills emit `pipx install game-of-cards` instead of cryptic Python tracebacks.
6. **Dogfood migration** (`migrate-phasor-agents-off-vendored-deckpy`) — phasor-agents itself currently vendors `deck.py`. Once `goc` is on PyPI, this repo deletes the vendored copy and shells to PATH like any other consumer. **Decision**: when (immediately after v1, or wait for v1.1)?

## Why this is high-contribution

- **Methodology survives platform churn.** Claude Code's plugin format, Cursor's `.cursor/rules/`, Codex's AGENTS.md — these will keep mutating. A self-contained PyPI CLI outlives any single agent's distribution surface.
- **Distribution unblocks adoption.** The methodology has unique structural properties (DoD blocks close, Andon-cord, Bellman value math, silent runtime). Without distribution, those properties die in this one repo. With distribution, the substrate is portable.
- **Schema discipline.** A versioned PyPI release with `goc upgrade --check` makes schema drift a real engineering concern (CI tests, migration scripts) instead of a per-repo accident.

## Decision

*Resolved 2026-05-03:* Approve scope as drafted: six sub-cards in package → install → AGENTS.md → bootstrap → multi-agent-shim → dogfood-migrate sequence

*Reasoning:* the six-sub-card decomposition mirrors the niche standard (Spec-Kit, BMAD, Agent OS, Ruler) and the dogfood migration on phasor-agents is the integration test that proves the whole epic; sub-card-level gates (v1 agent set, cutover timing) get decided independently when their cards are pulled
## Cross-references

- Existing in-repo installer: `Skill(use-game-of-cards)` — supersedes once `goc install` is on PyPI.
- Existing engine: `.claude/skills/deck/deck.py` — moves into the new package, deleted from this repo by sub-card 6.
- Schema versioning: `.claude/skills/card-schema/schema.yaml` (`schema_version: 3`) — the PyPI package's pinned schema with migration-on-upgrade.
- Peer landscape: Spec-Kit (github/spec-kit), BMAD-METHOD (bmadcode/BMAD-METHOD), Agent OS (buildermethods/agent-os), Ruler (intellectronica/ruler), claude-flow (ruvnet/claude-flow), AGENTS.md (agents.md, Linux Foundation).
- OpenCode skill compatibility: sst/opencode reads `.claude/skills/` natively with v1+v2 plugin format translation; hooks do NOT port.

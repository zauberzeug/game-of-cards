---
title: ship-game-of-cards-as-cross-agent-cli
summary: "Ship Game of Cards as a standalone, cross-agent CLI (`goc`) installable from PyPI, with durable project state under `.game-of-cards` and agent runtime affordances supplied optionally or through plugins. The CLI remains the engine; Claude Code, Codex, and later OpenClaw plugins provide skills/hooks without requiring consuming repos to check generated runtime files into source control."
status: open
stage: null
contribution: high
created: 2026-05-03
closed_at: null
human_gate: session
advances: []
advanced_by:
  - package-pyproject-and-pypi-release
  - install-command-scaffolds-repo
  - write-agentsmd-alongside-claudemd
  - multi-agent-shim-which-agents-at-v1
  - bootstrap-error-when-cli-not-on-path
  - drop-card-redirect-directories
  - surface-active-cards-in-board
  - support-external-game-of-cards-state-location
  - integrate-github-issues-discussions-and-pull-requests
  - support-custom-card-workflows-and-statuses
  - build-game-of-cards-project-website
  - restructure-comic-as-three-panels-and-add-audience-preamble
  - generate-plugin-payloads-from-templates-on-release
  - bundle-goc-engine-inside-plugin-payload
  - make-claude-md-and-agents-md-merge-opt-in-via-skill
  - support-worktrees-and-multi-agent-deck-sync
  - define-personas-and-use-cases-for-game-of-cards
  - explore-saas-deck-hosting-with-optional-tracker-sync
tags: [epic, infra, meta-fix]
definition_of_done: |
  - [ ] `game-of-cards` package published on PyPI; `pipx install game-of-cards` puts `goc` on PATH (sub-card: package-pyproject-and-pypi-release)
  - [ ] `goc install` scaffolds `.game-of-cards` project state and supports optional runtime affordances without requiring checked-in skills/hooks (sub-cards: install-command-scaffolds-repo, support-external-game-of-cards-state-location)
  - [ ] `goc install` writes/merges `AGENTS.md` so Codex/Cursor/OpenCode/Copilot/Aider see the methodology (sub-card: write-agentsmd-alongside-claudemd)
  - [ ] Agent runtime affordances exist for the supported set through opt-in repo-local shims or plugins; v1/v2 agent set decided and documented (sub-cards: multi-agent-shim-which-agents-at-v1, support-external-game-of-cards-state-location)
  - [ ] When `goc` is missing from PATH, skills/hooks emit one-line `pipx install game-of-cards` instructions instead of cryptic shell errors (sub-card: bootstrap-error-when-cli-not-on-path)
  - [ ] phasor-agents repo itself runs on PATH-resolved `goc`, vendored `.claude/skills/deck/deck.py` removed (tracked in phasor-agents: `goc-migrate-phasor-agents-off-vendored-deckpy`)
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

A standalone Python package — `game-of-cards` on PyPI, exposing the `goc` entry point — that absorbs the role of today's `.claude/skills/deck/deck.py` engine plus the `Skill(use-game-of-cards)` scaffolder. Every repo that wants the methodology runs `pipx install game-of-cards` once and `goc install` per-repo. Agent skills/hooks become optional runtime affordances, preferably plugin-provided where the agent supports that model.

```
pipx install game-of-cards            # machine-wide, once
cd any-repo
goc install                           # creates .game-of-cards project state and guidance
goc install --agents claude,codex     # optional repo-local shims where requested
goc upgrade                           # re-syncs skill templates from latest package version
goc kanban / goc new / goc done / ... # all existing deck.py verbs as top-level commands
```

The CLI is the engine; skills become trivial shells (`bash: goc new "$@"`, `bash: goc done "$@"`) whether they are installed repo-locally or supplied by an agent plugin. AGENTS.md remains the canonical cross-agent guidance surface; agent-specific files become deltas or plugin assets.

## How (high level — sub-cards have detail)

The initial work split into these in-repo streams, plus one phasor-agents dogfood card tracked in that repo:

1. **Packaging** (`package-pyproject-and-pypi-release`) — `pyproject.toml`, entry-point wiring, package-data layout for skill templates, PyPI release pipeline.
2. **Install command** (`install-command-scaffolds-repo`, updated by `support-external-game-of-cards-state-location`) — the `goc install` flow that creates `.game-of-cards` project state, guidance, and optional runtime affordances.
3. **AGENTS.md output** (`write-agentsmd-alongside-claudemd`) — write/merge AGENTS.md so the methodology is visible to all six major agent runtimes, not just Claude Code.
4. **Multi-agent shims** (`multi-agent-shim-which-agents-at-v1`) — `--agents` flag + per-agent shim templates. **Decision**: which agents at v1 (claude only? +cursor? +codex? +copilot?).
5. **Bootstrap UX** (`bootstrap-error-when-cli-not-on-path`) — when someone clones a GoC-using repo without `goc` installed, skills emit `pipx install game-of-cards` instead of cryptic Python tracebacks.
6. **Dogfood migration** (`../phasor-agents/deck/goc-migrate-phasor-agents-off-vendored-deckpy`) — phasor-agents itself currently vendors `deck.py`. Once `goc` is on PyPI, phasor-agents deletes the vendored copy and shells to PATH like any other consumer. **Decision**: immediate cutover on v1 release.
7. **Website** (`build-game-of-cards-project-website`) — project website and explanatory illustration for the public surface.
8. **GitHub/workflow extensions** (`integrate-github-issues-discussions-and-pull-requests`, `support-custom-card-workflows-and-statuses`) — session-gated compatibility and schema-extension work.

## Why this is high-contribution

- **Methodology survives platform churn.** Claude Code's plugin format, Cursor's `.cursor/rules/`, Codex's AGENTS.md — these will keep mutating. A self-contained PyPI CLI outlives any single agent's distribution surface.
- **Distribution unblocks adoption.** The methodology has unique structural properties (DoD blocks close, Andon-cord, Bellman value math, silent runtime). Without distribution, those properties die in this one repo. With distribution, the substrate is portable.
- **Schema discipline.** A versioned PyPI release with `goc upgrade --check` makes schema drift a real engineering concern (CI tests, migration scripts) instead of a per-repo accident.

## Decision

*Resolved 2026-05-03:* Approve scope as drafted: package → install → AGENTS.md → bootstrap → multi-agent-shim in this repo, with dogfood migration tracked in phasor-agents

*Reasoning:* the decomposition mirrors the niche standard (Spec-Kit, BMAD, Agent OS, Ruler) and the dogfood migration on phasor-agents is the integration test that proves the whole epic; sub-card-level gates (v1 agent set, cutover timing) get decided independently where their cards live
## Cross-references

- Existing in-repo installer: `Skill(use-game-of-cards)` — supersedes once `goc install` is on PyPI.
- Existing engine: `.claude/skills/deck/deck.py` — moves into the new package, deleted from this repo by sub-card 6.
- Schema versioning: `.claude/skills/card-schema/schema.yaml` (`schema_version: 3`) — the PyPI package's pinned schema with migration-on-upgrade.
- Peer landscape: Spec-Kit (github/spec-kit), BMAD-METHOD (bmadcode/BMAD-METHOD), Agent OS (buildermethods/agent-os), Ruler (intellectronica/ruler), claude-flow (ruvnet/claude-flow), AGENTS.md (agents.md, Linux Foundation).
- OpenCode skill compatibility: sst/opencode reads `.claude/skills/` natively with v1+v2 plugin format translation; hooks do NOT port.

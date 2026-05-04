---
title: readme-starter-card-and-doc-polish-session
summary: "Make the first-run story LLM-first: auto-detect Claude/Codex harnesses, install matching skills, invite users to create cards by prompting their agent, and align README/PyPI/GitHub metadata with that positioning."
status: active
stage: null
contribution: medium
created: 2026-05-04
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [documentation, story, infra]
definition_of_done: |
  - [ ] Implement `goc install` agent auto-detection: existing Claude usage installs `claude`, existing Codex usage installs `codex`, both markers install both, and no marker falls back to the documented default
  - [ ] Post-install output invites the user to create cards by prompting their LLM agent, not by leading with `goc new`; CLI commands remain available as engine/debug affordances
  - [ ] Rewrite README `Try it`, `Agent harnesses`, `What you get`, and `Status` so the LLM/agent interaction is the main interface and `goc` is described as the engine behind it
  - [ ] Review PyPI live metadata and local `[project]` metadata (`description`, `keywords`, classifiers, project URLs) so package discovery matches the LLM-first positioning
  - [ ] Review GitHub About/description/homepage/topics and update them to match the same positioning; remove topics for unshipped harnesses such as `openclaw`
  - [ ] Update `goc/install.py`, `tests/test_install.py`, and any harness manifests/templates touched by agent auto-detection
  - [ ] Smoke-test fresh installs for Claude-only, Codex-only, both-detected, and no-marker/default repos, including `goc`, `goc validate`, and an LLM-prompt-oriented next-step message
  - [ ] Record exact smoke-test commands/output in this card's `log.md`
  - [ ] `uv run goc validate` and relevant install tests pass after README/doc/code edits
---

# readme-starter-card-and-doc-polish-session

## Goal

Make the first five minutes match the intended product: users install
Game of Cards into a repo that already has an agent workflow, the
installer detects the agent surface already present, and the next step is
"ask your agent to create cards for the work you want" rather than "learn
the `goc` CLI".

The CLI remains central technically, but not as the primary user
interface. It is the engine that skills, guidance, hooks, and humans can
call when needed.

## Current evidence

- The live README checked on 2026-05-04 does **not** clearly promise
  automatic starter-card creation. It says `goc install` adds files and
  then shows `goc new "rename the button to Export"` as a command to run
  once installed.
- The phrase "starter set of GoC skills" appears in `README.md`; that is
  about installed skill templates, not a starter card. Keep the card
  focused on whether the first-run path is clear, not on chasing a stale
  promise that may already have been removed.
- `pyproject.toml` and `goc.__version__` are `0.0.2`, while the README
  `Status` section still says `0.0.1`. That is live documentation drift.
- PyPI live metadata checked on 2026-05-04 reports version `0.0.2`, but
  its rendered README still contains older copy: `goc install` "adds
  deck/, CLAUDE.md/AGENTS.md sections, a starter card" and the example
  still leads with CLI commands. The published package description is
  "Backlog tracking as a folder of markdown story-cards in your repo.
  Agent-readable. No proprietary state."
- GitHub live metadata checked on 2026-05-04:
  - description: "Agile development in the age of AI agents";
  - homepage: empty;
  - topics: `agents`, `agile`, `claude`, `claude-code`, `codex`,
    `openclaw`, `todo`, `workflow`.
  `openclaw` is premature while the OpenCLAW harness card is blocked, and
  the overall set does not yet say "LLM-first agent workflow" clearly.
- The current working tree also has a new README `Agent harnesses` section
  and an installer-manifest refactor under `goc/install.py` plus
  `goc/templates/agents/`. Treat those as live local context when doing the
  README pass, but do not widen this card into owning that refactor.
- `goc/install.py` currently creates the shared deck/config files and
  selected harness files. It creates `deck/log.md` and
  `deck/.goc-version`; it does **not** create `deck/<card>/README.md`.
- Fresh Codex smoke check from a temporary git repo:

  ```bash
  git init .
  uv run --project /Users/rodja/Projects/game-of-cards goc install --agents codex
  ```

  Output:

  ```text
  goc 0.0.2 installed for agents: codex.
  Next: `goc new my-first-card`. Run `goc upgrade` later to sync template updates.
  ```

  The install wrote `.codex/skills/`, `.game-of-cards/`, `.pre-commit-config.yaml`,
  `AGENTS.md`, `deck/log.md`, and `deck/.goc-version`. It wrote no card
  directory. `goc` and `goc validate` exited 0 with no output on the
  empty deck.

## Decision

*Resolved 2026-05-04:* Install should auto-detect existing Claude/Codex project usage, install matching harnesses, and present LLM prompting as the primary first-run interface rather than CLI card commands

*Reasoning:* Game of Cards is an agent-facing methodology substrate; users should experience the LLM workflow first while the goc CLI remains the engine behind the installed guidance

Implementation meaning:

- Detect Claude by repo-local Claude surfaces such as `CLAUDE.md`,
  `.claude/`, or `.mcp.json`/Claude-specific project config if the codebase
  already treats them as Claude signals.
- Detect Codex by repo-local Codex surfaces such as `AGENTS.md`,
  `.codex/`, or Codex-specific config.
- If both are present, install both harnesses.
- If neither is present, use the documented default and say how to request
  another harness explicitly.
- Keep explicit `--agents`, `--claude`, and `--codex` flags as overrides;
  auto-detection should not make scripted installs nondeterministic when
  an explicit agent set is provided.

## Session prompt

Walk through the README as a new user with an existing Claude or Codex
project. The first thing they should understand is: install GoC, then ask
the agent for persistent work; the agent uses the deck through `goc`
behind the scenes. CLI examples should be secondary, for users who want
to inspect or debug the engine directly.

## Scope

In scope:

- `README.md` sections `Try it`, `Agent harnesses`, `What you get`, and
  `Status`.
- `goc/install.py` auto-detection, post-install output, and help text.
- `tests/test_install.py` expectations if installer behavior or output
  changes.
- `pyproject.toml` public metadata: description, keywords, classifiers,
  and project URLs.
- GitHub repo About/description/homepage/topics.
- A fresh install smoke log for Claude-only, Codex-only, both-detected,
  and no-marker/default installs.

Out of scope:

- A broad brand rewrite of the README.
- New agent harnesses beyond the currently documented Claude/Codex split.
- PyPI release automation or release publishing, beyond documenting that a
  new release is required for PyPI to show updated README/metadata.
- Deck schema changes.

## Acceptance notes

- Do not imply `goc install` creates a card unless it actually does.
- Lead with an LLM prompt such as "Ask your agent: `create a card for
  renaming the export button`" rather than a `goc new ...` command.
- Make the installed artifact ownership clear:
  - shared every install: `deck/`, `.game-of-cards/`, `AGENTS.md`, and
    `.pre-commit-config.yaml`;
  - Claude harness: `.claude/skills/`, `.claude/hooks/user-prompt-submit-goc.py`,
    and `CLAUDE.md`;
  - Codex harness: `.codex/skills/` plus AGENTS.md-centered guidance.
- Reconcile `Agent harnesses` and `What you get` so they do not repeat
  slightly different harness facts.
- Avoid version text that will drift again unless the release process
  deliberately updates it. If a concrete version is kept in the README,
  verify it against `uv run goc --version`, `pyproject.toml`, and
  `goc.__version__` during closure.
- Suggested GitHub/PyPI metadata direction:
  - one-line description: "LLM-first backlog cards for coding agents,
    stored as markdown in your repo";
  - topics/keywords to consider: `ai-agents`, `llm`, `coding-agents`,
    `agents-md`, `claude-code`, `codex`, `kanban`, `agile`,
    `developer-tools`;
  - avoid `openclaw` until the OpenCLAW harness ships.

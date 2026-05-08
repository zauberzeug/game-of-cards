# Game of Cards — Claude Code Plugin

[Game of Cards](https://game-of-cards.com) (GoC) is an agile work-card
methodology for AI-agent collaborators. This plugin delivers the full GoC
skill and hook set to Claude Code in a single install step. No separate
package installation is required — the GoC CLI is bundled and runs via
the `uv` tool manager that ships with most developer environments.

## What's included

**14 skills** — invoked as `/skill-name` or `Skill(name)` inside Claude Code:

| Skill | Purpose |
|---|---|
| `kickoff` | Onboarding dialog — introduces GoC, scaffolds `.game-of-cards/` |
| `scan-deck` | Browse the board: triage view, filtered queues, decision Q&A |
| `next-card` | Pick the highest-leverage open card to work on next |
| `create-card` | File a new card with frontmatter and DoD scaffold |
| `advance-card` | Flip a card's status (open → active → blocked …) |
| `finish-card` | Close a card with DoD enforcement and commit |
| `decide-card` | Record a decision and lower a human gate |
| `pull-card` | Autonomous round: claim → work → close → commit |
| `refine-deck` | Hygiene pass — retag stale cards, prune old parks |
| `audit-deck` | Hunt for one undocumented defect or gap in the codebase |
| `standup` | Active cards, blockers, closures since yesterday, decision gates |
| `retrospective` | Cluster closed cards by tag, surface recurring failure modes |
| `card-schema` | Field reference — enums, canonical tags, DoD format |
| `deck` | Methodology front door and shared operating model |

**3 runtime hooks** — fire automatically, no configuration needed:

| Event | Hook | Purpose |
|---|---|---|
| `SessionStart` | `deck_session_start` | Prints active-card reminder; silent when no cards are in-flight |
| `UserPromptSubmit` | `deck_prompt_router` | Detects work-initiating prompts; injects a deck-first reminder |
| `Stop` | `pattern_generalization_check` | After code-mutating turns, prompts the agent to consider filing a generalization card |

## Install

```
/plugin marketplace add zauberzeug/game-of-cards
```

That's the only step. The plugin is self-contained — no `pip install` or
`pipx install` is needed. `uv` must be on your `PATH` (it usually is on
any machine with a modern Python toolchain; install from
[astral.sh/uv](https://docs.astral.sh/uv/) if it's missing).

## First use

After installing the plugin, start a new Claude Code session in any repo
and type:

```
/kickoff
```

Kickoff will introduce GoC, ask which working style fits your project
(solo / team / OSS-eval / agent-runtime), and scaffold the
`.game-of-cards/` project state directory. Once it completes, all 14
skills are immediately available.

For subsequent sessions the hooks fire automatically — you'll see an
active-card reminder at session start if work is already in flight.

## Requirements

- Claude Code (desktop app, web app, or IDE extension)
- `uv` on host `PATH`

## Links

- **Homepage**: [game-of-cards.com](https://game-of-cards.com)
- **Source**: [github.com/zauberzeug/game-of-cards](https://github.com/zauberzeug/game-of-cards)
- **License**: [MIT](https://github.com/zauberzeug/game-of-cards/blob/main/LICENSE)

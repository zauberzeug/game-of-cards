## Game of Cards — Claude Code specifics

The shared briefing is in [AGENTS.md](AGENTS.md) — three operating
modes (session / autonomous / Andon-cord), the `goc` CLI verb table,
and the deck philosophy apply to every runtime.

What's **Claude-specific** and lives only here:

### Plugin install (one-time per machine)

GoC skills and runtime hooks are delivered via the **GoC Claude Code
plugin** (`zauberzeug/game-of-cards`). The plugin lives in Claude Code's
user-level cache and works across all GoC repos without any checked-in
skill or hook files.

If the skills listed below don't respond, install the plugin once:

```
/plugin marketplace add zauberzeug/game-of-cards
/plugin install game-of-cards@game-of-cards
```

Plugin installs persist across repos and Claude Code sessions — this
is a one-time step per machine.

For repos that need skills and hooks checked into source control (CI
without plugin support, repos that fork or template GoC), the install
was done with `goc install --local-skills`. Running `goc upgrade`
on those repos will prompt to migrate to the plugin path, or pass
`--keep-local-skills` to keep the vendored layout.

### Skill surface (the 11 verbs as `Skill(...)`)

When the plugin is installed, the 11 GoC skills are available as
Claude Code's `Skill(...)` primitive:

- **Browse**: `Skill(scan-deck)` (triage default + filtered views + decision Q&A); `Skill(next-card)` (auto-pick highest-leverage gate=none card).
- **File new**: `Skill(create-card)` (scaffold frontmatter + DoD).
- **Advance**: `Skill(advance-card)` (status flip), `Skill(finish-card)` (close + DoD enforcement + commit).
- **Decide (human handoff)**: `Skill(decide-card)` (lowers gate decision/session → none).
- **Hygiene**: `Skill(improve-deck)` (retag stale, prune parks); `Skill(extend-deck)` (hunt new defects).
- **Reference**: `Skill(card-schema)` (required/optional fields, enums, canonical tags).
- **Autonomous**: `Skill(pull-card)` (one round of pull → claim → work → close → commit).
- **Overview**: `Skill(deck)` (methodology front door and shared operating model).

These wrap the same `goc <verb>` CLI documented in AGENTS.md, but
expose them as Claude Code's skill primitive so they're invokable
by name and can carry richer prompt scaffolding (decision rubrics,
Andon-cord guards, etc.).

### Runtime hooks

Three hooks fire automatically when the plugin is installed:

| Hook event | Script | Purpose |
|---|---|---|
| `SessionStart` | `deck_session_start` | Prints active-card reminder at session start; silent when no cards are in-flight. |
| `UserPromptSubmit` | `deck_prompt_router` | Detects work-initiating prompts; injects a deck-first reminder into Claude's view. |
| `Stop` | `pattern_generalization_check` | After code-mutating turns, asks the agent to self-assess whether the change warrants a generalization card. Opt-out: set `hooks.pattern_generalization_check: false` in `.game-of-cards/config.yaml`. |

The hooks are optional. Repos without the plugin still get full GoC
functionality through the `goc` CLI and AGENTS.md guidance. Other
agent runtimes (Codex, OpenCode, Cursor) use their own hook systems
and do not share this registration.

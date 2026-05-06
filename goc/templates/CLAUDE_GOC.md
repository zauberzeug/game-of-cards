## Game of Cards — Claude Code specifics

The shared briefing is in [AGENTS.md](AGENTS.md) — three operating
modes (session / autonomous / Andon-cord), the `goc` CLI verb table,
and the deck philosophy apply to every runtime.

What's **Claude-specific** and lives only here:

### Skill surface (the 11 verbs as `Skill(...)`)

Skills under `.claude/skills/` are **optional runtime affordances** installed
by `goc install --agents claude`. The core methodology works with just the
`goc` CLI; skills are convenience wrappers that surface the same verbs as
Claude Code's `Skill(...)` primitive. Repos that use GoC without a checked-in
Claude harness invoke the CLI directly via AGENTS.md guidance.

When installed, the 11 skills are:

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

### Runtime hooks and `.claude/settings.json`

`goc install --agents claude` installs three hook scripts and registers them
in `.claude/settings.json` so Claude Code actually executes them:

| Hook event | Script | Purpose |
|---|---|---|
| `SessionStart` | `.claude/hooks/deck_session_start.py` | Prints active-card reminder at session start; silent when no cards are in-flight. |
| `UserPromptSubmit` | `.claude/hooks/deck_prompt_router.py` | Detects work-initiating prompts; injects a deck-first reminder into Claude's view. |
| `Stop` | `.claude/hooks/pattern_generalization_check.py` | After code-mutating turns, asks the agent to self-assess whether the change is an instance of a broader pattern that warrants a generalization card. Opt-out: set `hooks.pattern_generalization_check: false` in `.game-of-cards/config.yaml`. |

**`.claude/settings.json`** is the Claude Code hook registration file — it is
what makes Claude Code invoke the scripts. `goc install` and `goc upgrade`
*merge* this file (adding GoC entries without removing your other settings or
hook registrations). It is **Claude-specific** and distinct from
`.game-of-cards/config.yaml`, which is the runtime-neutral GoC configuration
for workflow options and closure checks shared across all agent runtimes.

The hooks are optional. Repos without them still get full GoC functionality
through the `goc` CLI and AGENTS.md guidance; skills work regardless. Other
agent runtimes (Codex, OpenCode, Cursor) use their own hook systems and do
not share this registration. The prompt-router hook remains Claude-only.

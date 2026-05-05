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

### Silent runtime via `UserPromptSubmit` hook

`.claude/hooks/user-prompt-submit-goc.py` is an **optional** Claude-Code-only
hook installed by `goc install --agents claude`. It detects work-initiating
prompts and injects a deck-first reminder into Claude's view of the user
message. The reminder runs the silent pipeline
(`scan-deck → create-card → advance-card → implement → finish-card`)
without announcing card operations to the user. Vibe coders see code,
not bookkeeping.

The hook is not required for GoC to work — it is a convenience affordance.
Repos without it still get full GoC functionality through the `goc` CLI and
the AGENTS.md guidance. Other agent runtimes implement the same flow through
their own installed GoC skills or by invoking the CLI verbs from `AGENTS.md`.
The prompt hook remains Claude-only.

## Game of Cards — Claude Code specifics

The shared briefing is in [AGENTS.md](AGENTS.md) — three operating
modes (session / autonomous / Andon-cord), the `goc` CLI verb table,
and the deck philosophy apply to every runtime.

What's **Claude-specific** and lives only here:

### Skill surface (the 11 verbs as `Skill(...)`)

The methodology ships 11 Claude Code skills under `.claude/skills/`:

- **Browse**: `Skill(scan-deck)` (triage default + filtered views + decision Q&A); `Skill(next-card)` (auto-pick highest-leverage gate=none card).
- **File new**: `Skill(create-card)` (scaffold frontmatter + DoD).
- **Advance**: `Skill(advance-card)` (status flip), `Skill(finish-card)` (close + DoD enforcement + commit).
- **Decide (human handoff)**: `Skill(decide-card)` (lowers gate decision/session → none).
- **Hygiene**: `Skill(improve-deck)` (retag stale, prune parks); `Skill(extend-deck)` (hunt new defects).
- **Reference**: `Skill(card-schema)` (required/optional fields, enums, canonical tags).
- **Autonomous**: `Skill(pull-card)` (one round of pull → claim → work → close → commit).

These wrap the same `goc <verb>` CLI documented in AGENTS.md, but
expose them as Claude Code's skill primitive so they're invokable
by name and can carry richer prompt scaffolding (decision rubrics,
Andon-cord guards, etc.).

### Silent runtime via `UserPromptSubmit` hook

`.claude/hooks/user-prompt-submit-goc.py` is a Claude-Code-only hook
(Codex/Cursor/OpenCode/Copilot do not have an equivalent). It detects
work-initiating prompts and injects a deck-first reminder into Claude's
view of the user message. The reminder runs the silent pipeline
(`scan-deck → create-card → advance-card → implement → finish-card`)
without announcing card operations to the user. Vibe coders see code,
not bookkeeping.

Other agent runtimes implement the same flow, but invoked explicitly
by the user ("file a card for X", "show the deck") rather than
auto-detected from prompt phrasing.

---
title: shrink-root-guidance-files-by-moving-content-into-skills
summary: "AGENTS.md (132 lines / ~6.9 KB) and CLAUDE.md (105 lines / ~5.2 KB) are loaded into baseline session context for every GoC repo — every prompt pays the token cost. Most of that content (deck-mode flowchart, verb table, YAML format rules, worker-field semantics, multi-team coordination opt-ins, marker-block explanation) is reference material the agent only needs at the moment of acting. Move that content into the relevant skill bodies (`Skill(deck)`, `Skill(card-schema)`, `Skill(create-card)`, etc.) where it loads on-demand. The root files shrink to a thin pointer: 'this repo uses Game of Cards; the methodology lives in skills, run `Skill(deck)` for an overview' plus the discovery marker. Goal: cut baseline context tokens by ~80% while preserving discoverability."
status: active
stage: null
contribution: high
created: 2026-05-10
closed_at: null
human_gate: none
advances:
  - write-agentsmd-alongside-claudemd
advanced_by: []
tags: [story, infra, documentation]
definition_of_done: |
  - [ ] Audit the current `AGENTS_GOC.md` and `CLAUDE_GOC.md` templates section-by-section; classify each section as KEEP-AT-ROOT (discovery + thin pointer) or MOVE-TO-SKILL (reference material consulted at action time)
  - [ ] Map MOVE-TO-SKILL sections to specific skill targets — verb table → `card-schema` skill, deck-mode flowchart → `deck` skill, YAML format / worker-field rules → `card-schema` skill, multi-team coordination opt-ins → `kickoff` skill, marker-block explanation → install/upgrade docs (not a skill)
  - [ ] New `AGENTS_GOC.md` is ≤ 25 lines: discovery marker + one-paragraph orientation + `goc --help` pointer + skill-invocation pointer (host-agnostic phrasing: "ask the agent to invoke its `deck` / `card-schema` / `create-card` capability")
  - [ ] New `CLAUDE_GOC.md` is ≤ 15 lines: `@AGENTS.md` import + minimal Claude-only deltas (plugin install link if not already covered by `Skill(kickoff)`)
  - [ ] Skill bodies updated to absorb their share of the moved content; each skill stays focused on one verb (don't dump the full briefing into one skill)
  - [ ] Token-cost A/B: measure baseline session context before/after on a representative GoC repo; document the savings in the closure log entry
  - [ ] No information lost — every piece of MOVE-TO-SKILL content has a documented home in a skill, not just deleted
  - [ ] `goc upgrade` migrates existing repos: re-syncs the slimmer marker block, leaves user content above/below untouched
  - [ ] Plugin payload re-synced via `python scripts/sync_plugin_assets.py` and OpenClaw skill port re-run
  - [ ] Smoke test on a fresh repo: kickoff completes; agent can file/advance/finish a card using only the skills (no need to grep root files for verb syntax or YAML rules)
worker: {who: "claude[bot]", where: main}
---

# Shrink root guidance files by moving content into skills

## Why

Reported 2026-05-10: the GoC briefing files at the repo root pay a
context-token tax on every session, even when the agent isn't doing
deck work. Today's footprint:

| File | Lines | Bytes |
|---|---|---|
| `goc/templates/AGENTS_GOC.md` | 132 | 6882 |
| `goc/templates/CLAUDE_GOC.md` | 105 | 5190 |
| **Total baseline context** | **237** | **12072** |

For Claude Code with `@AGENTS.md` import in CLAUDE.md, all 12 KB lands
in the system prompt at session start. For the silent UserPromptSubmit
hook reminder, additional tokens are injected per work-initiating
prompt. The agent rarely *acts on* most of this content — the YAML
format rules for `advances:` lists are only relevant when editing
frontmatter; the worker-field semantics matter only when a worker is
named; multi-team coordination opt-ins are inert in single-user repos.

**Reference material consulted at action time should live in the
skill that does the action, not in the always-loaded baseline.**
That's the entire reason Claude Code's skills primitive exists —
on-demand prompt scaffolding without baseline cost.

The AGENTS.md/CLAUDE.md split established by
`write-agentsmd-alongside-claudemd` is correct in shape (one
host-agnostic file, one Claude-specific delta) but wrong in size. Both
files should be tiny pointers. The skills carry the methodology.

## What

**New target sizes:**

- `AGENTS_GOC.md`: ≤ 25 lines. Discovery marker + one-paragraph
  orientation + how to ask the agent to do deck work + pointer to
  `goc --help` and the relevant skill names.
- `CLAUDE_GOC.md`: ≤ 15 lines. `@AGENTS.md` import + Claude-only
  deltas (plugin install link, the silent-runtime hook explanation
  IF that's not already in `Skill(deck)`).

**Content moves (proposed):**

| Current section in AGENTS.md | Lines | Moves to |
|---|---|---|
| "Three operating modes" (session/autonomous/Andon-cord) | ~50 | `Skill(deck)` body |
| Daily verb table | ~12 | `Skill(card-schema)` body or new pointer skill |
| YAML format rules (`advances:` block-style etc.) | ~5 | `Skill(card-schema)` body |
| `worker` field semantics | ~7 | `Skill(advance-card)` body (claim time is when worker is set) |
| "What lives where" (project state vs runtime) | ~15 | `Skill(kickoff)` body (one-time setup concern) |
| Multi-team coordination opt-ins | ~10 | `Skill(kickoff)` or a new `multi-team` skill |
| Discovery marker + thin orientation | ~10 | Stays at root |

| Current section in CLAUDE.md | Lines | Moves to |
|---|---|---|
| Plugin install (one-time per machine) | ~25 | `Skill(claude-kickoff)` body (already half there) |
| First-use kickoff guidance | ~30 | `Skill(kickoff)` and `Skill(claude-kickoff)` (already covered) |
| Skill surface listing (12 verbs) | ~15 | Redundant — Claude Code's skill registry already knows them |
| Runtime hooks table | ~10 | `Skill(claude-kickoff)` body or remove (hooks register via plugin) |
| `@AGENTS.md` import + thin Claude-only delta | ~5 | Stays at root |

## How

**Step 1 — Classify.** Walk both templates section by section; tag each
heading KEEP / MOVE / DELETE. Where MOVE, name the target skill.

**Step 2 — Move content into skills.** For each MOVE section, edit the
target skill's `SKILL.md` to incorporate the content. Watch for
duplication with what the skill already says — merge rather than
append. Per-skill body should stay focused: don't dump the verb table
into `Skill(create-card)` just because cards have verbs.

**Step 3 — Rewrite the root templates.** New `AGENTS_GOC.md` and
`CLAUDE_GOC.md` are the thin pointers. Discovery marker stays so
agent runtimes still see "this repo uses GoC."

**Step 4 — Validate no information is lost.** For each MOVE entry, the
content must be reachable through the named skill. Reachability test:
ask "if the agent is about to file a card, will it see the YAML format
rules?" — answer should be yes (via `Skill(create-card)` invoking
`Skill(card-schema)` for the predicate table, or by direct skill body
inclusion).

**Step 5 — Token-cost measurement.** Before/after baseline session
context on a representative GoC repo. Document savings in
`log.md` closure entry — the *why* this card existed.

**Step 6 — Migration.** `goc upgrade` re-syncs the slimmer marker
block. User content above/below the markers survives.

## Why this is high-contribution

- Every GoC session pays this cost, every prompt — multiplicative
  savings.
- Aligns with Claude Code's skill primitive design (load on demand).
- Forces a discipline check on the root files: anything we keep there
  must justify always-loaded status.
- Makes the methodology more discoverable through the skill registry
  rather than through document reading.

## Cross-references

- Builds on `write-agentsmd-alongside-claudemd` (which established the
  split this card refines into thin pointers).
- Sibling: `kickoff-asks-where-goc-briefing-lives` — that card lets
  the user pick *which* root file holds the briefing; this card
  shrinks *what's in* the briefing. Both can ship in either order;
  the shrink card makes the briefing-target choice less fraught
  because either way the file is small.
- Reproduced 2026-05-10 from the `/tmp/goc-usage` kickoff inspection.

## Open questions (non-blocking, decide during implementation)

- Should the host-agnostic flowchart live in `Skill(deck)` (one place
  to look) or be split per-mode across `Skill(create-card)`,
  `Skill(pull-card)`, `Skill(decide-card)` (mode lives next to the
  skill that uses it)? Default to centralized in `Skill(deck)`
  unless the implementer finds a reason otherwise — the deck skill
  is the front door already.
- Does removing the verb table from AGENTS.md break agents that don't
  invoke skills (e.g., a simple-shell-only Codex session)? Mitigation:
  AGENTS.md retains a one-line `goc --help` pointer; the verb table is
  one shell command away.

## Out of scope

- Renaming or restructuring the skills themselves. This card moves
  content INTO existing skills, not creating new skill primitives.
- Removing AGENTS.md/CLAUDE.md entirely. The discovery marker stays
  at root by convention (agentic AI Foundation guidance).
- Skill body length policy. If a target skill's body grows large after
  absorbing moved content, that's a separate refactor card to file.

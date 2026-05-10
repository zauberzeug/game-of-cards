---
title: kickoff-asks-where-goc-briefing-lives
summary: "Today `goc install` writes the GoC briefing block into BOTH `AGENTS.md` (full body) AND `CLAUDE.md` (Claude-specific delta + `@AGENTS.md` import). Even though the second file imports the first rather than duplicating it, having two root-level files with overlapping concerns reads as duplication to a fresh user. Replace the silent dual-write with a kickoff dialog that asks the user where the briefing should live — `AGENTS.md`, `CLAUDE.md`, or `CLAUDE.local.md` — defaulting based on persona. claude-kickoff then ensures Claude Code can find it: if the briefing is in AGENTS.md or CLAUDE.local.md, write a one-line `@<file>` import into CLAUDE.md (or skip CLAUDE.md entirely if the user wants a single-file install)."
status: done
stage: null
contribution: medium
created: 2026-05-10
closed_at: 2026-05-10
human_gate: none
advances:
  - write-agentsmd-alongside-claudemd
advanced_by: []
tags: [story, infra, documentation]
definition_of_done: |
  - [x] `kickoff` skill asks the user a single question after the persona step: "Where should the GoC briefing live?" — options: `AGENTS.md` (recommended for cross-runtime / agent-runtime persona), `CLAUDE.md` (recommended for Claude-only / team), `CLAUDE.local.md` (recommended for solo personal use, not checked in)
  - [x] Persona drives the recommendation order but does NOT lock the choice — user sees all three options every time
  - [x] `goc install` accepts a target file from the kickoff (env var, CLI flag, or config) and writes the marker-bounded block ONLY into the chosen file; other candidates are not touched
  - [x] When the chosen file is NOT `CLAUDE.md`, `claude-kickoff` writes/merges a minimal `CLAUDE.md` that contains only `@<chosen-file>` (so Claude Code transitively loads the briefing)
  - [x] When the chosen file IS `CLAUDE.md`, no AGENTS.md is written by GoC (user can still create one manually); document this trade-off (cross-runtime visibility lost)
  - [x] `goc upgrade` re-syncs only the chosen file's marker block; existing installs (which have blocks in both AGENTS.md and CLAUDE.md) are migrated forward — prompt user to pick one home, then strip the block from the others
  - [x] CLAUDE.md and AGENTS.md templates updated so the chosen-home file carries the FULL briefing (currently CLAUDE.md is a "Claude-specific delta" assuming AGENTS.md is co-present); when user chooses CLAUDE.md as sole home, the Claude-specific extras still belong but the delta-style cross-link to AGENTS.md must collapse
  - [x] Smoke test: kickoff three fresh repos, one per choice; verify Claude Code sees the briefing in all three (via `@AGENTS.md` import for the AGENTS.md and CLAUDE.local.md paths)
  - [x] Plugin payload re-synced via `python scripts/sync_plugin_assets.py` and the OpenClaw skill port re-run if skill bodies changed
worker: {who: "claude[bot]", where: main}
---

# Kickoff asks where the GoC briefing lives

## Why

Reported by Rodja 2026-05-10 after inspecting `/tmp/goc-usage` (an empty
non-git dir post-kickoff): "I find it worrysome to have AGENTS.md and
CLAUDE.md with same content."

The current install writes the GoC marker-bounded block into BOTH files:

- `AGENTS.md` — full host-agnostic briefing (deck-first mode, verb table,
  Andon-cord, pull semantics).
- `CLAUDE.md` — Claude-specific delta (plugin install, Skill() surface,
  hook table) PLUS `@AGENTS.md` import to load the host-agnostic briefing.

The content is *not* literally duplicated — CLAUDE.md uses `@AGENTS.md` to
pull AGENTS.md into Claude's context — but to a fresh reader, two
root-level guidance files with overlapping concerns and matching
`<!-- BEGIN GOC -->` markers read as duplication. The split was
established by `write-agentsmd-alongside-claudemd` to ensure both Claude
and non-Claude runtimes see the briefing without copy-paste; the
trade-off was visual repetition at the root.

For solo Claude users (the most common kickoff persona), AGENTS.md is
dead weight — they have no Codex / Cursor / OpenCode session to feed it.
For agent-runtime users, AGENTS.md is the canonical home and CLAUDE.md is
overhead. **Persona should drive the choice, and the choice should be one
file, not two.**

## What

A new step in `kickoff` between the persona question and `goc install`:

> "Where should the GoC briefing live in this repo?"
>
> 1. **AGENTS.md** — read by Codex, Cursor, Copilot, OpenCode, Aider, and
>    Claude Code (via `@AGENTS.md` import). Recommended for cross-runtime
>    / agent-runtime / OSS-eval personas.
> 2. **CLAUDE.md** — read only by Claude Code. Recommended for Claude-only
>    / team personas.
> 3. **CLAUDE.local.md** — read only by Claude Code, gitignored.
>    Recommended for solo personal use where the deck is private.

Persona-driven default ordering (e.g. `solo` → CLAUDE.local.md first;
`team` → CLAUDE.md first; `agent-runtime` / `oss-eval` → AGENTS.md first)
but all three options always offered.

After the user picks:

- `goc install` writes the marker-bounded block into ONLY the chosen file.
- If the chosen file is `AGENTS.md` or `CLAUDE.local.md`, `claude-kickoff`
  ensures Claude Code can find it by writing/merging a minimal
  `CLAUDE.md` containing just the line `@<chosen-file>` (inside a marker
  block so `goc upgrade` can re-sync).
- If the chosen file is `CLAUDE.md`, no separate AGENTS.md is written;
  the file carries the full briefing including the Claude-specific
  extras. Cross-runtime visibility is intentionally given up — surface
  this trade-off in the kickoff dialog so the user knows.

## How

**Code surfaces touched:**

1. `goc/templates/skills/kickoff/SKILL.md` — add the new question; pass
   the answer to `goc install` via a flag (e.g. `--briefing-target
   AGENTS.md` / `CLAUDE.md` / `CLAUDE.local.md`).
2. `goc/install.py` — `_sync_methodology_blocks` (line ~719) currently
   hard-codes AGENTS_GUIDANCE writing AGENTS.md. Generalize to accept
   the target path.
3. `goc/templates/AGENTS_GOC.md` and `goc/templates/CLAUDE_GOC.md` —
   today the CLAUDE template assumes AGENTS.md is co-present
   (`@AGENTS.md` import + Claude delta). When CLAUDE.md is the sole home,
   the template needs to collapse the host-agnostic content inline. Two
   options:
   - **(a)** Keep two templates; merge them inline at install time when
     CLAUDE.md is sole home.
   - **(b)** One unified template with the Claude-specific extras gated
     by a flag.
   Option (a) is simpler — pick that unless implementer finds a reason.
4. `goc/templates/skills/claude-kickoff/SKILL.md` — when chosen file is
   not `CLAUDE.md`, write the minimal `@<file>` import into `CLAUDE.md`
   (in a marker block).
5. `goc upgrade` — migration path for existing installs that already
   have blocks in BOTH files: detect, prompt user to pick one home,
   strip the block from the other.

**Open question (pre-implementation):**

When user picks `CLAUDE.md` as sole home, do we leave AGENTS.md alone
(if pre-existing user content exists) or refuse to install if AGENTS.md
exists? Default proposal: never touch AGENTS.md when CLAUDE.md is
chosen; users with both have a methodology drift problem to resolve
manually. This keeps GoC's surface small.

## Why this is medium-contribution

- Clear scope: one new dialog turn, one new install flag, one template
  collapse, one upgrade migration.
- High UX leverage: removes the most common new-user confusion (two
  guidance files, why?).
- Reversible: `goc upgrade` can re-sync if the user's choice changes.

## Cross-references

- Parent: builds on `write-agentsmd-alongside-claudemd` (which
  established the dual-write pattern this card replaces with a choice).
  Marked in `advances:` for that reason.
- Sibling: `kickoff-and-install-handle-non-git-directories` (filed same
  session) — both are kickoff-skill edits but in different code paths.
- Not blocked by anything; can be pulled standalone.

## Out of scope

- Adding more briefing-target options (e.g. `.cursor/rules/`,
  `.codex/AGENTS.md`). The three proposed cover the persona spectrum;
  more can be added later if a runtime-specific install path emerges.
- Redesigning the marker-block format. The `<!-- BEGIN GOC v… -->`
  pattern stays.
- Auto-detecting which file the user "probably wants" without asking.
  Per feedback: ask explicitly, recommend by persona.

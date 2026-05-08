---
name: kickoff
description: Kick off GoC in a fresh repo — introduce GoC, ask which persona fits, confirm per-file AGENTS.md / CLAUDE.md / CLAUDE.local.md merges, run infrastructure preflight, then scaffold project state. AUTO-INVOKE when the user says "kickoff", "use GoC here", "set up game of cards", "initialize GoC", or when any GoC skill is first used in a repo with no `.game-of-cards/deck/` directory.
---

# Kick off GoC in this repo

This skill is the **project onboarding dialog**: it introduces GoC, asks a
few focused questions, checks that the infrastructure is ready, then runs
`goc install` with the flags that match the user's answers. It runs
**idempotently** — every stage detects on-disk state before asking, so a
re-run on a partially set-up repo only asks for the answers it cannot
already derive. There is no mid-flow restart: the `goc install` step
relies on Claude Code's interactive permission prompt when
`Bash(goc:*)` is not pre-allowed, and any settings.json write happens
LAST so a context-losing restart never destroys work-in-progress.

> **Updating the plugin?** Run `/plugin marketplace update zauberzeug/game-of-cards`
> before `/plugin install` — Claude Code reuses its local marketplace clone and does
> not refresh it automatically. Skipping this step silently installs the old bytes.

## Stage 0 — state detection sweep

Read all of the on-disk signals at once. Each subsequent stage will skip
its question(s) when the corresponding signal is already present.

```bash
ls .game-of-cards/deck/ 2>/dev/null && echo "DECK_EXISTS" || echo "deck_missing"
which goc 2>/dev/null && echo "GOC_ON_PATH" || echo "goc_missing"
grep -l '<!-- BEGIN GOC' CLAUDE.md 2>/dev/null && echo "CLAUDE_MD_MERGED" || true
grep -l '<!-- BEGIN GOC' AGENTS.md 2>/dev/null && echo "AGENTS_MD_MERGED" || true
test -f CLAUDE.local.md && echo "CLAUDE_LOCAL_MD_EXISTS" || true
```

Read the project's `.claude/settings.json` and `~/.claude/settings.json`
with the Read tool. Note whether `"Bash(goc:*)"` appears in either
`permissions.allow` array.

Route on the results:

- **`DECK_EXISTS`** → report "GoC is already initialized in this repo —
  deck is live." and **stop**. Do not continue. This is the silent-exit
  branch the skill description promises.
- **`goc_missing`** → halt at this stage. Tell the user: "`goc` CLI is
  not installed. The plugin's bundled `goc` should resolve via
  `${CLAUDE_PLUGIN_ROOT}/bin/goc` on `PATH`. If that's not happening,
  install via `uv tool install game-of-cards` (or `pipx install
  game-of-cards`) and re-run kickoff." Do not proceed without `goc`.
- **Otherwise** → continue. Hold the detected flags in mind through the
  rest of the flow.

---

## Stage 1 — introduce GoC

Skip this stage if **any** of these signals were detected in Stage 0:
`CLAUDE_MD_MERGED`, `AGENTS_MD_MERGED`, `CLAUDE_LOCAL_MD_EXISTS`, or
`Bash(goc:*)` is in either settings.json. Their presence means the user
has engaged with kickoff before; replaying the intro is noise.

Otherwise, deliver this paragraph verbatim (no edits, no summarising):

> **Game of Cards (GoC)** is a lightweight, file-based methodology layer
> for software projects. It keeps a deck of cards — each card is a plain
> Markdown file with YAML frontmatter — that records every piece of
> persistent work: features, bugs, decisions, and experiments. The deck
> tracks status, value, and dependency edges between cards, so AI agents
> and human contributors share one authoritative view of what's in flight
> and what's next. GoC borrows from XP (user stories, spike experiments),
> Kanban (pull-based intake, explicit WIP limits), and Scrum (definition
> of done, backlog refinement). The CLI (`goc`) validates cards, renders
> board views, and gates closure on a per-card definition of done.

Then pause — do not continue to Stage 2 until the user acknowledges or
responds.

---

## Stage 2 — persona question

Skip this stage if **all three** of CLAUDE.md, AGENTS.md, and
CLAUDE.local.md already have their final state on disk (i.e., the
detection signals from Stage 0 already determine every Stage 3 answer).
The persona question only drives Stage 3 defaults; if Stage 3 has
nothing left to ask, persona is moot.

Otherwise, ask the user **one question**:

> Which description best fits how you'll use GoC here?
>
> 1. **Solo / vibe-coder** — I'm the only contributor; I want a lightweight
>    personal task tracker with AI-agent help.
> 2. **Classical team** — We have a shared repo, multiple humans, and want
>    the deck as a shared source of truth alongside PRs and reviews.
> 3. **OSS / library evaluator** — I'm exploring GoC before deciding whether
>    to adopt it; I'd prefer not to merge anything into AGENTS.md or CLAUDE.md
>    yet.
> 4. **Agent-runtime / CI** — This repo is driven primarily by AI agents;
>    I want hooks and the CLI but minimal checked-in documentation overhead.

Record the user's answer. It drives routing in Stage 3.

| Persona | Stage 3 default |
|---|---|
| Solo / vibe-coder | Skip CLAUDE.md merge; offer AGENTS.md only |
| Classical team | Offer all three files; surface the external-deck-location guidance |
| OSS / library evaluator | Default all three to **No** — user must opt in explicitly |
| Agent-runtime / CI | Default CLAUDE.md and AGENTS.md to **No**; offer CLAUDE.local.md only |

---

## Stage 3 — per-file merge opt-in

For each of the three files, skip the question if Stage 0 detected its
final state on disk. Use the persona defaults from Stage 2 for any
question that still needs asking.

**Question A — CLAUDE.md** (skip if `CLAUDE_MD_MERGED` was detected)

> Merge GoC guidance into `CLAUDE.md`? This adds a `<!-- BEGIN GOC -->` block
> with Claude Code-specific instructions (skill surface, hook descriptions,
> first-use setup). The block is marker-bounded and survives future `goc upgrade`
> runs. Your existing content above and below the markers is untouched.
>
> Add to CLAUDE.md? [yes/no]

**Question B — AGENTS.md** (skip if `AGENTS_MD_MERGED` was detected)

> Merge GoC guidance into `AGENTS.md`? This adds a `<!-- BEGIN GOC -->` block
> with agent-neutral instructions (deck philosophy, CLI verb table, operating
> modes). Suitable for Codex, OpenAI Code, and any runtime that reads AGENTS.md.
>
> Add to AGENTS.md? [yes/no]

**Question C — CLAUDE.local.md** (skip if `CLAUDE_LOCAL_MD_EXISTS` was
detected; otherwise prompt only if the user answered No to both A and B,
or if persona is agent-runtime)

> Add a minimal `CLAUDE.local.md` stub? This gives Claude Code a private,
> untracked file to record project-local notes without touching checked-in
> docs.
>
> Create CLAUDE.local.md stub? [yes/no]

If the persona is **Classical team**, add after all three questions:

> **Team tip:** For teams that keep the deck outside the repo (e.g., a shared
> network drive or separate Git repo), see the card
> `support-external-game-of-cards-state-location` — it tracks the design work
> for configurable deck paths.

Record the three answers (or, for skipped questions, record the detected
state as the answer). Pass them to Stage 4 as flags for `goc install`.

---

## Stage 4 — scaffold project state

Summarise the three merge answers collected in Stage 3, then ask:

> Ready to scaffold? This will create `.game-of-cards/` and the files you
> selected above. Confirm? [yes/no]

On confirmation, build the `goc install` invocation from the Stage 3 answers:

- If the user said **Yes** to CLAUDE.md and AGENTS.md: `goc install` (defaults merge both)
- If the user said **No** to CLAUDE.md only: `goc install --no-claude-md`
- If the user said **No** to AGENTS.md only: `goc install --no-agents-md`
- If the user said **No** to both: `goc install --no-claude-md --no-agents-md`
- If CLAUDE.local.md was requested: create a minimal stub after `goc install` runs

> **Note for this repo (game-of-cards source tree):** Translate bare `goc`
> commands to `uv run goc` when working in the goc package source tree itself.

Run `goc install` directly. If `Bash(goc:*)` is not pre-allowed, Claude
Code's interactive permission prompt fires — that is expected. The user
clicks "yes (always allow)" once, Claude Code records the grant in the
project's `.claude/settings.json` automatically, and the install
proceeds. **No restart is required.** If the grant is refused, halt
and report; do not attempt to bypass.

`goc install` writes project state and merges GoC guidance blocks into the
requested files, but does NOT install `.claude/skills/` or `.claude/hooks/`
— those come from the plugin.

After `goc install` returns, verify `.game-of-cards/deck/` exists before
continuing.

---

## Stage 5 — persist permission for future sessions

If Stage 0 detected `Bash(goc:*)` already in either settings.json (or
the interactive grant in Stage 4 wrote it), this stage is a no-op.

Otherwise, write the project's `.claude/settings.json` with:

```json
{
  "permissions": {
    "allow": ["Bash(goc:*)"]
  }
}
```

Merge with any existing `.claude/settings.json` content rather than
overwriting it. After the file is written, tell the user:

> `Bash(goc:*)` is now permitted for this project's future Claude Code
> sessions. The current session continues to work without a restart.

This is the LAST mutation kickoff makes. If a future enhancement ever
needs a session restart, it must remain after this point so a context-
losing restart never destroys work that has already been done.

---

## Stage 6 — confirm ready and suggest next step

Report to the user:

```
GoC is set up. All skills are live. What should the first card be?
```

The deck is now live. `Skill(create-card)`, `Skill(scan-deck)`, and all
other GoC skills work immediately — no further kickoff needed.
